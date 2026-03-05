"""
Phase 3: TikTok API 업로드 자동화

담당 에이전트: content-director.md (최종 승인)
역할: 완성된 영상을 스케줄에 따라 TikTok에 자동 업로드

파이프라인:
  schedule.json + final/*.mp4 + metadata/*.json
    → TikTok OAuth 인증
    → Video Upload API
    → 발행 처리 완료 폴링
    → 발행 확인 리포트

입력:
  outputs/{date}/schedule.json          ← 발행 스케줄
  outputs/{date}/final/*_edited.mp4     ← 편집 완성본
  outputs/{date}/metadata/*.json        ← 캡션·해시태그·발행시간

출력:
  outputs/{date}/upload_log.json        ← 업로드 결과 로그

사용법:
  python -X utf8 pipeline/05_upload.py
  python -X utf8 pipeline/05_upload.py --date 2026-03-01
  python -X utf8 pipeline/05_upload.py --dry-run  (실제 업로드 없이 확인만)
"""

import argparse
import json
import os
import time
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import load_config, setup_output_dir, load_json, save_json

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok 영상 업로드 자동화")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--config", default="config/config.json")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--index", type=int)
    return parser.parse_args()


def load_token_cache(config_dir: Path) -> dict | None:
    """저장된 TikTok 토큰 로드."""
    token_path = config_dir / ".tiktok_token.json"
    if token_path.exists():
        with open(token_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def get_access_token(config: dict, config_dir: Path) -> str:
    """
    캐시된 토큰 반환. 없으면 OAuth URL 출력 후 사용자 입력 대기.

    웹 어드민 사용 시: /api/upload/auth/url → 브라우저에서 인증 → 토큰 자동 캐시
    CLI 사용 시: 아래 지침에 따라 수동 인증
    """
    token_data = load_token_cache(config_dir)
    if token_data:
        access_token = token_data.get("access_token", "")
        if access_token:
            print("  [인증] 캐시된 토큰 사용")
            return access_token

    cfg = config.get("tiktok", {})
    client_key = os.environ.get(cfg.get("client_key_env", "TIKTOK_CLIENT_KEY"), "")

    if not client_key:
        print("  오류: TIKTOK_CLIENT_KEY 환경변수가 설정되지 않았습니다.")
        print("  웹 어드민(http://localhost:8000)에서 TikTok 연결 후 다시 실행하세요.")
        sys.exit(1)

    print("  TikTok 인증이 필요합니다.")
    print("  웹 어드민(http://localhost:8000/schedule)에서 'TikTok 연결'을 클릭하세요.")
    print("  인증 완료 후 이 스크립트를 다시 실행하세요.")
    sys.exit(1)


def initialize_upload(video_path: Path, access_token: str, api_base: str) -> dict:
    """TikTok Content Posting API: 업로드 초기화."""
    if httpx is None:
        raise ImportError("httpx 패키지가 필요합니다: pip install httpx")

    file_size = video_path.stat().st_size
    # 청크 크기: 64MB
    chunk_size = 64 * 1024 * 1024
    chunk_count = max(1, (file_size + chunk_size - 1) // chunk_size)

    payload = {
        "post_info": {
            "privacy_level": "MUTUAL_FOLLOW_FRIENDS",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": file_size,
            "chunk_size": min(chunk_size, file_size),
            "total_chunk_count": chunk_count,
        },
    }

    with httpx.Client() as client:
        resp = client.post(
            f"{api_base}/post/publish/video/init/",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            timeout=30.0,
        )

    if resp.status_code != 200:
        raise RuntimeError(f"업로드 초기화 실패: {resp.text}")

    data = resp.json()
    return {
        "publish_id": data.get("data", {}).get("publish_id", ""),
        "upload_url": data.get("data", {}).get("upload_url", ""),
    }


def upload_video_chunks(video_path: Path, upload_url: str) -> bool:
    """영상 청크 단위 업로드."""
    if httpx is None:
        return False

    chunk_size = 64 * 1024 * 1024
    file_size = video_path.stat().st_size

    with open(video_path, "rb") as f, httpx.Client() as client:
        chunk_index = 0
        offset = 0
        while True:
            data = f.read(chunk_size)
            if not data:
                break
            end = min(offset + len(data) - 1, file_size - 1)
            resp = client.put(
                upload_url,
                content=data,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes {offset}-{end}/{file_size}",
                    "Content-Length": str(len(data)),
                },
                timeout=120.0,
            )
            if resp.status_code not in (200, 206):
                print(f"  청크 {chunk_index} 업로드 실패: {resp.status_code}")
                return False
            offset += len(data)
            chunk_index += 1
            print(f"  청크 {chunk_index} 업로드됨 ({offset}/{file_size} bytes)")

    return True


def publish_video(publish_id: str, metadata: dict, access_token: str, api_base: str) -> dict:
    """업로드된 영상 발행 처리."""
    if httpx is None:
        return {}

    caption = metadata.get("caption", "")
    hashtags = metadata.get("hashtags", [])
    # 캡션에 해시태그 포함
    full_caption = f"{caption}\n{' '.join(hashtags)}"[:2200]

    payload = {
        "post_id": publish_id,
        "post_info": {
            "title": full_caption,
            "privacy_level": "MUTUAL_FOLLOW_FRIENDS",
        },
    }

    with httpx.Client() as client:
        resp = client.post(
            f"{api_base}/post/publish/video/",
            json=payload,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            timeout=30.0,
        )

    if resp.status_code != 200:
        print(f"  발행 요청 실패: {resp.text}")
        return {}

    return resp.json().get("data", {})


def poll_upload_status(publish_id: str, access_token: str, api_base: str, max_retries: int = 10) -> str:
    """업로드 처리 완료 폴링."""
    if httpx is None:
        return "UNKNOWN"

    for attempt in range(max_retries):
        with httpx.Client() as client:
            resp = client.post(
                f"{api_base}/post/publish/status/fetch/",
                json={"publish_id": publish_id},
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30.0,
            )

        if resp.status_code == 200:
            status = resp.json().get("data", {}).get("status", "UNKNOWN")
            print(f"  상태: {status} (시도 {attempt + 1}/{max_retries})")
            if status in ("PUBLISH_COMPLETE", "FAILED"):
                return status

        time.sleep(30)

    return "TIMEOUT"


def find_video_for_index(final_dir: Path, video_index: int) -> Path | None:
    """영상 인덱스에 맞는 파일 탐색."""
    pattern = f"{video_index:02d}_*_edited.mp4"
    matches = list(final_dir.glob(pattern))
    return matches[0] if matches else None


def find_metadata_for_index(metadata_dir: Path, video_index: int) -> dict | None:
    """메타데이터 파일 로드."""
    pattern = f"{video_index:02d}_*.json"
    matches = list(metadata_dir.glob(pattern))
    if not matches:
        return None
    with open(matches[0], encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    output_dir = setup_output_dir(config["pipeline"]["output_base_dir"], args.date)
    config_dir = Path("config")

    print(f"[05_upload] TikTok 업로드 시작 — {args.date}")
    if args.dry_run:
        print("  [DRY RUN] 실제 업로드 없이 검증만 실행")

    # 스케줄 로드
    schedule_path = output_dir / "schedule.json"
    if not schedule_path.exists():
        print(f"오류: schedule.json이 없습니다 — {schedule_path}")
        sys.exit(1)
    schedule = load_json(schedule_path)
    videos = schedule.get("videos", [])

    if args.index:
        videos = [v for v in videos if v.get("index") == args.index]

    final_dir = output_dir / "final"
    metadata_dir = output_dir / "metadata"

    if not args.dry_run:
        access_token = get_access_token(config, config_dir)

    api_base = config.get("tiktok", {}).get("api_base_url", "https://open.tiktokapis.com/v2")

    results = []
    for video_plan in videos:
        idx = video_plan.get("index", 1)
        topic = video_plan.get("topic", f"영상{idx}")
        print(f"\n  [{idx}] {topic} 업로드 중...")

        video_path = find_video_for_index(final_dir, idx)
        metadata = find_metadata_for_index(metadata_dir, idx)

        if not video_path:
            print(f"  오류: 영상 파일 없음 (final/{idx:02d}_*_edited.mp4)")
            results.append({"index": idx, "topic": topic, "status": "FILE_NOT_FOUND"})
            continue

        if not metadata:
            print(f"  경고: 메타데이터 없음, 기본값 사용")
            metadata = {"caption": topic, "hashtags": [], "publish_at": ""}

        print(f"  파일: {video_path.name} ({video_path.stat().st_size // 1024 // 1024}MB)")

        if args.dry_run:
            print(f"  [DRY RUN] 업로드 시뮬레이션 완료")
            results.append({"index": idx, "topic": topic, "status": "DRY_RUN", "file": video_path.name})
            continue

        try:
            print("  업로드 초기화 중...")
            init_data = initialize_upload(video_path, access_token, api_base)
            publish_id = init_data["publish_id"]
            upload_url = init_data["upload_url"]
            print(f"  publish_id: {publish_id}")

            print("  청크 업로드 중...")
            success = upload_video_chunks(video_path, upload_url)
            if not success:
                raise RuntimeError("청크 업로드 실패")

            print("  발행 요청 중...")
            pub_result = publish_video(publish_id, metadata, access_token, api_base)

            print("  발행 완료 대기 중...")
            final_status = poll_upload_status(publish_id, access_token, api_base)

            results.append({
                "index": idx,
                "topic": topic,
                "status": final_status,
                "publish_id": publish_id,
                "video_id": pub_result.get("video_id", ""),
            })
            print(f"  ✓ {final_status}")

        except Exception as e:
            print(f"  오류: {e}")
            results.append({"index": idx, "topic": topic, "status": "ERROR", "error": str(e)})

    # 결과 로그 저장
    log_path = output_dir / "upload_log.json"
    save_json({"date": args.date, "results": results}, log_path)
    print(f"\n[05_upload] 완료")
    print(f"  → {log_path}")


if __name__ == "__main__":
    main()
