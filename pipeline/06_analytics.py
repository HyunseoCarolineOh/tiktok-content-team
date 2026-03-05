"""
Phase 4: 성과 분석 및 전략 최적화

담당 에이전트: analyst.md
역할: TikTok Analytics 수집 → 주간 리포트 생성 → A/B 테스트 분석 → 전략 피드백

파이프라인:
  TikTok Analytics API
    → 영상별 성과 지표 수집
    → 후크 A/B 비교 분석
    → Claude(analyst) 고성과 패턴 추출
    → 주간 리포트 마크다운 생성

출력:
  outputs/{date}/report.md            ← 주간 성과 리포트
  outputs/{date}/analytics.json       ← 원시 성과 데이터

사용법:
  python -X utf8 pipeline/06_analytics.py
  python -X utf8 pipeline/06_analytics.py --date 2026-03-01
  python -X utf8 pipeline/06_analytics.py --mock  (테스트용 더미 데이터)
"""

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import load_config, setup_output_dir, load_agent_prompt, save_json
from pipeline import claude_client

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok 성과 분석 + 주간 리포트")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--config", default="config/config.json")
    parser.add_argument("--mock", action="store_true")
    return parser.parse_args()


def load_mock_data() -> tuple[dict, list[dict]]:
    """테스트용 더미 성과 데이터."""
    channel = {
        "followers": 1250,
        "followers_delta": 87,
        "total_views": 45320,
        "profile_views": 312,
    }
    videos = [
        {"video_id": "v001", "title": "창업자 90%가 모르는 것", "views": 12400, "completion_rate": 0.52, "likes": 380, "comments": 45, "shares": 120, "saves": 280, "follows": 38},
        {"video_id": "v002", "title": "스타트업 PMF 찾는 법", "views": 8200, "completion_rate": 0.41, "likes": 210, "comments": 28, "shares": 65, "saves": 195, "follows": 22},
        {"video_id": "v003", "title": "네카라쿠배 이직 전략", "views": 9800, "completion_rate": 0.47, "likes": 295, "comments": 62, "shares": 88, "saves": 240, "follows": 31},
        {"video_id": "v004", "title": "B2B 영업 클로징 기술", "views": 7100, "completion_rate": 0.38, "likes": 185, "comments": 19, "shares": 42, "saves": 160, "follows": 15},
        {"video_id": "v005", "title": "SaaS 가격 전략 실전", "views": 7820, "completion_rate": 0.44, "likes": 230, "comments": 34, "shares": 71, "saves": 215, "follows": 26},
    ]
    return channel, videos


def fetch_channel_analytics(access_token: str, date_range: tuple, api_base: str) -> dict:
    """TikTok Analytics API로 채널 성과 수집."""
    if httpx is None:
        return {}

    start_date, end_date = date_range
    with httpx.Client() as client:
        resp = client.get(
            f"{api_base}/research/user/info/",
            params={
                "fields": "follower_count,following_count,likes_count,video_count",
                "start_date": start_date,
                "end_date": end_date,
            },
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )
    if resp.status_code != 200:
        print(f"  경고: 채널 분석 API 실패 ({resp.status_code})")
        return {}
    return resp.json().get("data", {})


def fetch_video_analytics(video_ids: list[str], access_token: str, api_base: str) -> list[dict]:
    """영상별 성과 지표 수집."""
    if httpx is None or not video_ids:
        return []

    with httpx.Client() as client:
        resp = client.post(
            f"{api_base}/research/video/query/",
            json={
                "filters": {"video_ids": video_ids},
                "fields": ["id", "title", "view_count", "like_count", "comment_count",
                           "share_count", "save_count", "average_time_watched"],
                "max_count": 20,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )
    if resp.status_code != 200:
        print(f"  경고: 영상 분석 API 실패 ({resp.status_code})")
        return []
    return resp.json().get("data", {}).get("videos", [])


def analyze_ab_test(upload_log: dict, video_analytics: list[dict]) -> dict:
    """후크 A vs B 성과 비교 분석."""
    results = upload_log.get("results", []) if upload_log else []

    # 후크 버전별 completion_rate 평균
    a_rates = [v.get("completion_rate", 0) for v in video_analytics[:2]]
    b_rates = [v.get("completion_rate", 0) for v in video_analytics[2:4]]

    a_avg = sum(a_rates) / len(a_rates) if a_rates else 0
    b_avg = sum(b_rates) / len(b_rates) if b_rates else 0

    return {
        "winner": "A" if a_avg >= b_avg else "B",
        "a_avg_completion": round(a_avg, 3),
        "b_avg_completion": round(b_avg, 3),
        "insights": f"후크 {'A' if a_avg >= b_avg else 'B'} 버전이 시청 완료율이 더 높음",
    }


def extract_performance_patterns(video_analytics: list[dict], config: dict) -> dict:
    """Claude(analyst)로 고성과 영상 패턴 추출."""
    system_prompt = load_agent_prompt("analyst")
    analytics_json = json.dumps(video_analytics, ensure_ascii=False, indent=2)

    user_message = f"""
다음 TikTok 영상 성과 데이터를 분석해주세요.

영상 데이터:
{analytics_json}

분석 항목:
1. 고성과 영상의 제목/주제 패턴
2. 시청 완료율 vs 조회수 상관관계
3. 저장/공유 비율이 높은 콘텐츠 유형
4. 다음 주 개선 전략 3가지

JSON 형식으로 반환:
{{
  "top_performer": {{
    "video_id": "...",
    "title": "...",
    "reason": "고성과 이유"
  }},
  "patterns": [
    "패턴 1",
    "패턴 2",
    "패턴 3"
  ],
  "recommendations": [
    "다음 주 전략 1",
    "다음 주 전략 2",
    "다음 주 전략 3"
  ],
  "weak_areas": ["개선 필요 영역"]
}}

순수 JSON만 반환하세요.
"""

    try:
        result = claude_client.call_json(system_prompt, user_message, max_tokens=8192)
        return result if isinstance(result, dict) else {}
    except Exception as e:
        print(f"  경고: 패턴 분석 실패 ({e})")
        # 기본 분석
        if video_analytics:
            top = max(video_analytics, key=lambda v: v.get("views", 0))
            return {
                "top_performer": {"video_id": top.get("video_id", ""), "title": top.get("title", ""), "reason": "최다 조회수"},
                "patterns": ["높은 조회수 = 강한 후크 활용", "저장율 높은 콘텐츠 = 실전 팁"],
                "recommendations": ["후크 강도 높이기", "실전 예시 추가", "발행 시간 최적화"],
                "weak_areas": ["시청 완료율 개선 필요"],
            }
        return {}


def generate_weekly_report(
    channel: dict,
    videos: list[dict],
    ab_result: dict,
    patterns: dict,
    target_date: str,
    output_dir: Path,
) -> None:
    """주간 성과 리포트 마크다운 생성."""
    lines = [
        f"## 주간 성과 리포트 — {target_date}",
        "",
        "### 📊 채널 성과 요약",
        f"- 팔로워: {channel.get('followers', 0):,}명 (+{channel.get('followers_delta', 0)}명)",
        f"- 총 조회수: {channel.get('total_views', 0):,}회",
        f"- 프로필 방문: {channel.get('profile_views', 0):,}회",
        "",
        "### 🎬 영상별 성과",
        "| 제목 | 조회수 | 완료율 | 좋아요 | 저장 | 공유 |",
        "|---|---|---|---|---|---|",
    ]

    for v in videos:
        completion = f"{v.get('completion_rate', 0) * 100:.1f}%"
        lines.append(
            f"| {v.get('title', '')} "
            f"| {v.get('views', 0):,} "
            f"| {completion} "
            f"| {v.get('likes', 0):,} "
            f"| {v.get('saves', 0):,} "
            f"| {v.get('shares', 0):,} |"
        )

    lines += [
        "",
        "### 🔬 후크 A/B 비교",
        f"- 승자: **후크 {ab_result.get('winner', '?')}**",
        f"- A 평균 완료율: {ab_result.get('a_avg_completion', 0) * 100:.1f}%",
        f"- B 평균 완료율: {ab_result.get('b_avg_completion', 0) * 100:.1f}%",
        f"- 인사이트: {ab_result.get('insights', '')}",
        "",
        "### 💡 고성과 패턴",
    ]

    for pattern in patterns.get("patterns", []):
        lines.append(f"- {pattern}")

    top = patterns.get("top_performer", {})
    if top:
        lines += [
            "",
            f"**최고 성과 영상**: {top.get('title', '')}",
            f"이유: {top.get('reason', '')}",
        ]

    lines += ["", "### 🚀 다음 주 전략"]
    for rec in patterns.get("recommendations", []):
        lines.append(f"1. {rec}")

    lines += ["", "### ⚠️ 개선 필요 영역"]
    for weak in patterns.get("weak_areas", []):
        lines.append(f"- {weak}")

    report_path = output_dir / "report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → {report_path}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    output_dir = setup_output_dir(config["pipeline"]["output_base_dir"], args.date)

    print(f"[06_analytics] 성과 분석 시작 — {args.date}")

    if args.mock:
        print("  [MOCK] 테스트 데이터 사용")
        channel, videos = load_mock_data()
    else:
        # 실제 API 인증 + 데이터 수집
        from pipeline.utils import load_json
        token_path = Path("config") / ".tiktok_token.json"
        if not token_path.exists():
            print("  오류: TikTok 토큰이 없습니다. 웹 어드민에서 인증 후 재시도하세요.")
            print("  또는 --mock 플래그로 테스트 데이터 사용")
            sys.exit(1)

        token_data = load_json(token_path)
        access_token = token_data.get("access_token", "")
        api_base = config.get("tiktok", {}).get("api_base_url", "https://open.tiktokapis.com/v2")

        # 날짜 범위 (7일 전 ~ 오늘)
        end = args.date
        start_dt = __import__("datetime").datetime.strptime(args.date, "%Y-%m-%d") - timedelta(days=7)
        start = start_dt.strftime("%Y%m%d")

        print("  [API] 채널 성과 수집 중...")
        channel = fetch_channel_analytics(access_token, (start, end), api_base)

        # 업로드 로그에서 video_id 추출
        upload_log_path = output_dir / "upload_log.json"
        video_ids = []
        if upload_log_path.exists():
            upload_log = load_json(upload_log_path)
            video_ids = [r.get("video_id", "") for r in upload_log.get("results", []) if r.get("video_id")]

        print("  [API] 영상 성과 수집 중...")
        videos = fetch_video_analytics(video_ids, access_token, api_base)

        if not videos:
            print("  경고: 영상 데이터 없음, mock 데이터로 대체")
            _, videos = load_mock_data()

    # 업로드 로그 로드 (A/B 분석용)
    upload_log_path = output_dir / "upload_log.json"
    upload_log = {}
    if upload_log_path.exists():
        with open(upload_log_path, encoding="utf-8") as f:
            upload_log = json.load(f)

    print("  [분석] A/B 테스트 분석 중...")
    ab_result = analyze_ab_test(upload_log, videos)

    print("  [Claude] 고성과 패턴 추출 중...")
    patterns = extract_performance_patterns(videos, config)

    generate_weekly_report(channel, videos, ab_result, patterns, args.date, output_dir)

    # 원시 데이터 저장
    analytics_path = output_dir / "analytics.json"
    save_json({"channel": channel, "videos": videos, "ab_result": ab_result, "patterns": patterns}, analytics_path)
    print(f"  → {analytics_path}")

    print(f"[06_analytics] 완료")


if __name__ == "__main__":
    main()
