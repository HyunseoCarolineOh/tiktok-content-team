"""
Phase 1 - Step 3: 스크립트 자동 생성

담당 에이전트: scriptwriter.md
역할: 5개 영상 각각의 스크립트 + 메타데이터 자동 생성

파이프라인:
  schedule.json → Claude(scriptwriter) → 스크립트(.txt) + 메타데이터(.json) 저장

입력:
  outputs/{date}/schedule.json      ← 02_planning.py 출력

출력:
  outputs/{date}/scripts/01_제목.txt    ← 프롬프터 형식 스크립트
  outputs/{date}/metadata/01_제목.json  ← 캡션·해시태그·발행시간

사용법:
  python -X utf8 pipeline/03_scripting.py
  python -X utf8 pipeline/03_scripting.py --date 2026-03-01
  python -X utf8 pipeline/03_scripting.py --index 1
"""

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import load_config, setup_output_dir, load_agent_prompt, load_brand_guide, load_json, save_json
from pipeline import claude_client


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok 스크립트 자동 생성")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--config", default="config/config.json")
    parser.add_argument("--index", type=int, help="특정 영상만 생성 (1-5)")
    return parser.parse_args()


def load_schedule(output_dir: Path) -> dict:
    """02_planning.py가 생성한 스케줄 로드."""
    return load_json(output_dir / "schedule.json")  # type: ignore


def generate_script(video_plan: dict, config: dict, brand_guide: dict) -> dict:
    """
    Claude API(scriptwriter)로 스크립트 생성. (streaming 출력)

    반환값:
        {"hook_a": str, "hook_b": str, "body": {"point1": str, "point2": str, "point3": str}, "cta": str}
    """
    system_prompt = load_agent_prompt("scriptwriter")
    duration = config.get("pipeline", {}).get("script_duration_seconds", 60)
    tone = brand_guide.get("tone_of_voice", {})
    cta_templates = brand_guide.get("cta_templates", [])
    forbidden = brand_guide.get("forbidden_content", {})

    user_message = f"""
다음 영상 기획을 바탕으로 TikTok 스크립트를 작성해주세요.

영상 정보:
- 주제: {video_plan.get('topic')}
- 각도/관점: {video_plan.get('angle')}
- 카테고리: {video_plan.get('category')}
- 핵심 포인트: {json.dumps(video_plan.get('key_points', []), ensure_ascii=False)}
- 후크 방향: {video_plan.get('hook_direction', '통계형')}
- 감정 타겟: {video_plan.get('target_emotion', '호기심')}

작성 기준:
- 총 분량: {duration}초 (약 {duration * 4}~{duration * 5}자)
- 말투: {tone.get('primary', '전문적이지만 친근하게')}
- 피해야 할 표현: {', '.join(forbidden.get('words', []))}
- 금지 주장: {', '.join(forbidden.get('claims', []))}

CTA 예시 (하나 선택 또는 변형):
{json.dumps(cta_templates, ensure_ascii=False)}

다음 JSON 형식으로 반환:
{{
  "hook_a": "후크 버전 A (충격 통계 또는 반전 진술, 15자 이내)",
  "hook_b": "후크 버전 B (질문형 또는 도전형, 15자 이내)",
  "body": {{
    "point1": "첫 번째 핵심 포인트 (3-4줄)",
    "point2": "두 번째 핵심 포인트 (3-4줄)",
    "point3": "세 번째 핵심 포인트 (3-4줄)"
  }},
  "cta": "콜투액션 (10자 이내)"
}}

순수 JSON만 반환하세요.
"""

    # retro 기반 콘텐츠이면 추가 컨텍스트 삽입 (API 호출 횟수 동일)
    if video_plan.get("source") == "retro":
        user_message += f"""

[회고 기반 콘텐츠 지침]
원본 회고 텍스트: {video_plan.get('original_text', '')}
톤: 솔직한 1인칭 경험담 + 실용적 인사이트
후크 방향: {video_plan.get('hook_direction', '경험고백형')}
"""

    print(f"    [Claude] 스크립트 생성 중 (streaming)...")
    full_text = ""
    try:
        for chunk in claude_client.call_streaming(system_prompt, user_message, max_tokens=4096):
            print(chunk, end="", flush=True)
            full_text += chunk
        print()  # 줄바꿈

        # JSON 파싱
        raw = full_text.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(raw)
    except Exception as e:
        print(f"\n  경고: 스크립트 생성 실패 ({e}), 기본 스크립트 사용")
        topic = video_plan.get('topic', '주제')
        return {
            "hook_a": f"{topic}의 충격적 진실",
            "hook_b": f"당신이 {topic}에 대해 모르는 것",
            "body": {
                "point1": "첫 번째 핵심 포인트를 여기에 작성하세요.",
                "point2": "두 번째 핵심 포인트를 여기에 작성하세요.",
                "point3": "세 번째 핵심 포인트를 여기에 작성하세요.",
            },
            "cta": "팔로우하고 더 보기",
        }


def generate_metadata(video_plan: dict, script: dict, config: dict, brand_guide: dict) -> dict:
    """Claude API로 메타데이터 생성."""
    system_prompt = load_agent_prompt("scriptwriter")
    must_tags = brand_guide.get("hashtag_strategy", {}).get("must_include", [])
    rotate_tags = brand_guide.get("hashtag_strategy", {}).get("rotate", [])
    max_tags = brand_guide.get("hashtag_strategy", {}).get("max_count", 30)

    user_message = f"""
다음 스크립트와 영상 정보를 바탕으로 TikTok 메타데이터를 생성해주세요.

영상 주제: {video_plan.get('topic')}
후크 A: {script.get('hook_a')}
CTA: {script.get('cta')}
발행 시간: {video_plan.get('publish_at', '')}

필수 해시태그 (반드시 포함): {json.dumps(must_tags, ensure_ascii=False)}
선택 해시태그 풀 (적절히 선택): {json.dumps(rotate_tags, ensure_ascii=False)}
최대 해시태그 수: {max_tags}개

다음 JSON 형식으로 반환:
{{
  "caption": "TikTok 캡션 (150자 이내, 이모지 포함)",
  "hashtags": ["#태그1", "#태그2", ...],
  "publish_at": "{video_plan.get('publish_at', '')}",
  "thumbnail_text": "썸네일 텍스트 (15자 이내, 강렬하게)"
}}

순수 JSON만 반환하세요.
"""

    try:
        result = claude_client.call_json(system_prompt, user_message, max_tokens=2048)
        if isinstance(result, dict):
            # 필수 해시태그 보장
            hashtags = result.get("hashtags", [])
            for tag in must_tags:
                if tag not in hashtags:
                    hashtags.insert(0, tag)
            result["hashtags"] = hashtags[:max_tags]
            return result
    except Exception as e:
        print(f"  경고: 메타데이터 생성 실패 ({e}), 기본값 사용")

    return {
        "caption": f"💡 {video_plan.get('topic', '')} | 비즈니스 인사이트",
        "hashtags": must_tags + rotate_tags[:5],
        "publish_at": video_plan.get("publish_at", ""),
        "thumbnail_text": video_plan.get("topic", "")[:15],
    }


def _safe_filename(topic: str) -> str:
    """파일명으로 안전한 문자열 변환."""
    # 특수문자 제거 및 공백 → 언더스코어
    safe = re.sub(r'[\\/*?:"<>|]', '', topic)
    safe = safe.replace(' ', '_')
    return safe[:30]  # 최대 30자


def save_script(script: dict, video_plan: dict, scripts_dir: Path) -> Path:
    """스크립트 텍스트 파일 저장."""
    idx = video_plan.get("index", 1)
    title = _safe_filename(video_plan.get("topic", f"영상{idx}"))
    filename = f"{idx:02d}_{title}.txt"
    path = scripts_dir / filename

    lines = [
        f"# {video_plan.get('topic')}",
        f"# 카테고리: {video_plan.get('category', '')}",
        f"# 각도: {video_plan.get('angle', '')}",
        "",
        "## 후크 A",
        script.get("hook_a", ""),
        "",
        "## 후크 B",
        script.get("hook_b", ""),
        "",
        "## 본문",
        script.get("body", {}).get("point1", ""),
        "",
        script.get("body", {}).get("point2", ""),
        "",
        script.get("body", {}).get("point3", ""),
        "",
        "## CTA",
        script.get("cta", ""),
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def save_metadata(metadata: dict, video_plan: dict, metadata_dir: Path) -> Path:
    """메타데이터 JSON 저장."""
    idx = video_plan.get("index", 1)
    title = _safe_filename(video_plan.get("topic", f"영상{idx}"))
    filename = f"{idx:02d}_{title}.json"
    path = metadata_dir / filename
    # retro 시드 필드 보존
    if "seed_id" in video_plan:
        metadata["seed_id"] = video_plan["seed_id"]
        metadata["retro_date"] = video_plan.get("retro_date", "")
    save_json(metadata, path)
    return path


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    brand_guide = load_brand_guide()
    output_dir = setup_output_dir(config["pipeline"]["output_base_dir"], args.date)

    scripts_dir = output_dir / "scripts"
    metadata_dir = output_dir / "metadata"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)

    print(f"[03_scripting] 스크립트 생성 시작 — {args.date}")

    schedule = load_schedule(output_dir)
    videos = schedule.get("videos", [])

    if args.index:
        videos = [v for v in videos if v["index"] == args.index]

    for video in videos:
        print(f"  [{video['index']}/5] {video['topic']} 스크립트 생성 중...")
        script = generate_script(video, config, brand_guide)
        metadata = generate_metadata(video, script, config, brand_guide)
        script_path = save_script(script, video, scripts_dir)
        meta_path = save_metadata(metadata, video, metadata_dir)
        print(f"    → {script_path.name}")
        print(f"    → {meta_path.name}")

    print(f"[03_scripting] 완료 — {len(videos)}개 스크립트 생성")


if __name__ == "__main__":
    main()
