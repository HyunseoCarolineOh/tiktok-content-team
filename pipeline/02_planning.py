"""
Phase 1 - Step 2: 주간 콘텐츠 기획

담당 에이전트: content-director.md + researcher.md
역할: 주제 풀에서 5개 선정 + 주간 콘텐츠 캘린더 생성

파이프라인:
  topics_pool.json → Claude(content-director) → 5개 선정 → schedule.json 저장

입력:
  outputs/{date}/topics_pool.json   ← 01_research.py 출력

출력:
  outputs/{date}/schedule.json      ← 주간 발행 스케줄 (5개 영상)
  outputs/{date}/plan_summary.md    ← 기획 요약 마크다운

사용법:
  python -X utf8 pipeline/02_planning.py
  python -X utf8 pipeline/02_planning.py --date 2026-03-01
"""

import argparse
import json
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.utils import load_config, setup_output_dir, load_agent_prompt, load_json, save_json
from pipeline import claude_client
from pipeline.seed_loader import load_pending_seeds, seed_to_topic, mark_seeds_as_used
from pipeline.record_traceability import record_link


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="주간 콘텐츠 캘린더 생성")
    parser.add_argument("--date", default=str(date.today()))
    parser.add_argument("--config", default="config/config.json")
    return parser.parse_args()


def load_topics_pool(output_dir: Path) -> list[dict]:
    """01_research.py가 생성한 주제 풀 로드."""
    return load_json(output_dir / "topics_pool.json")  # type: ignore


def select_weekly_topics(topics: list[dict], config: dict) -> list[dict]:
    """
    Claude(content-director)가 주간 5개 주제 선정.

    콘텐츠 믹스:
    - 트렌드 인사이트 2개
    - 실전 전략 1개
    - 케이스 스터디 1개
    - 커뮤니티 참여 1개
    """
    system_prompt = load_agent_prompt("content-director")
    topics_json = json.dumps(topics, ensure_ascii=False, indent=2)
    weekly_count = config.get("pipeline", {}).get("weekly_video_count", 5)

    user_message = f"""
다음 주제 풀에서 이번 주 TikTok 영상 {weekly_count}개를 선정해주세요.

콘텐츠 믹스 기준:
- 트렌드 인사이트: 2개 (시의성 높은 주제)
- 실전 전략: 1개 (즉시 적용 가능한 팁)
- 케이스 스터디: 1개 (실제 기업 사례)
- 커뮤니티 참여: 1개 (댓글 유도, 의견 묻기)

주제 풀:
{topics_json}

결과를 JSON 배열로 반환:
[
  {{
    "index": 1,
    "topic": "주제명",
    "category": "트렌드 인사이트",
    "angle": "구체적 각도/관점",
    "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
    "hook_direction": "후크 방향성 (통계형/반전형/질문형)",
    "target_emotion": "호기심/놀람/공감"
  }}
]

순수 JSON만 반환하세요.
"""

    print("  [Claude] 주간 주제 선정 중...")
    try:
        result = claude_client.call_json(system_prompt, user_message, max_tokens=4096)
        if isinstance(result, list):
            return result[:weekly_count]
        return result.get("selected", [])[:weekly_count] if isinstance(result, dict) else []
    except Exception as e:
        print(f"  경고: 주제 선정 실패 ({e}), 상위 5개 사용")
        high_priority = [t for t in topics if t.get("priority") == "high"] or topics
        return [
            {
                "index": i + 1,
                "topic": t.get("topic", f"주제 {i+1}"),
                "category": ["트렌드 인사이트", "트렌드 인사이트", "실전 전략", "케이스 스터디", "커뮤니티 참여"][i],
                "angle": t.get("angle", "실전 관점"),
                "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"],
                "hook_direction": "통계형",
                "target_emotion": "호기심",
            }
            for i, t in enumerate(high_priority[:5])
        ]


def generate_schedule(selected_topics: list[dict], start_date: str, config: dict) -> dict:
    """최적 발행 시간 기반 스케줄 생성."""
    optimal_times = config.get("schedule", {}).get("optimal_post_times", ["07:00", "12:00", "19:00", "21:00"])
    timezone = config.get("schedule", {}).get("timezone", "Asia/Seoul")

    # 월~금 발행 기준, 최적 시간 순환
    start = datetime.strptime(start_date, "%Y-%m-%d")
    # 월요일 기준으로 맞추기
    days_to_monday = start.weekday()
    week_start = start - timedelta(days=days_to_monday)

    videos = []
    time_cycle = optimal_times * 2  # 5개까지 커버
    for i, topic in enumerate(selected_topics):
        post_day = week_start + timedelta(days=i)
        post_time = time_cycle[i % len(time_cycle)]
        h, m = post_time.split(":")
        publish_at = post_day.replace(hour=int(h), minute=int(m), second=0)
        # ISO8601 +09:00
        publish_str = publish_at.strftime("%Y-%m-%dT%H:%M:%S") + "+09:00"

        entry = {
            "index": topic.get("index", i + 1),
            "topic": topic.get("topic", ""),
            "category": topic.get("category", ""),
            "angle": topic.get("angle", ""),
            "key_points": topic.get("key_points", []),
            "hook_direction": topic.get("hook_direction", ""),
            "target_emotion": topic.get("target_emotion", ""),
            "publish_at": publish_str,
        }
        # retro 시드 필드 전달
        for field in ("source", "seed_id", "retro_date", "original_text"):
            if field in topic:
                entry[field] = topic[field]
        videos.append(entry)

    return {"week": start_date, "generated_at": start.isoformat(), "videos": videos}


def save_schedule(schedule: dict, output_dir: Path) -> None:
    """schedule.json 저장."""
    path = output_dir / "schedule.json"
    save_json(schedule, path)
    print(f"  → {path}")


def generate_plan_summary(selected_topics: list[dict], schedule: dict, output_dir: Path) -> None:
    """기획 요약 마크다운 저장."""
    lines = [
        f"## 주간 콘텐츠 기획 — {schedule.get('week', '')}",
        "",
        "| # | 주제 | 카테고리 | 후크 방향 | 발행 시간 |",
        "|---|---|---|---|---|",
    ]
    for v in schedule.get("videos", []):
        publish = v.get("publish_at", "")[:16].replace("T", " ")
        lines.append(
            f"| {v.get('index')} | {v.get('topic')} | {v.get('category')} "
            f"| {v.get('hook_direction')} | {publish} |"
        )

    lines += ["", "### 영상별 핵심 포인트", ""]
    for v in schedule.get("videos", []):
        lines.append(f"#### {v.get('index')}. {v.get('topic')}")
        lines.append(f"각도: {v.get('angle', '')}")
        for kp in v.get("key_points", []):
            lines.append(f"- {kp}")
        lines.append("")

    path = output_dir / "plan_summary.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  → {path}")


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    output_dir = setup_output_dir(config["pipeline"]["output_base_dir"], args.date)

    print(f"[02_planning] 주간 콘텐츠 기획 시작 — {args.date}")

    topics = load_topics_pool(output_dir)
    print(f"  {len(topics)}개 주제 풀 로드됨")

    selected = select_weekly_topics(topics, config)

    # 규칙: retro 시드가 있으면 마지막 자리에 강제 삽입 (Claude 추가 호출 없음)
    pending_seeds = load_pending_seeds(max_seeds=1)
    if pending_seeds:
        retro_topic = seed_to_topic(pending_seeds[0])
        if len(selected) >= 5:
            selected[-1] = retro_topic
        else:
            selected.append(retro_topic)
        # index 재정렬
        for i, t in enumerate(selected):
            t["index"] = i + 1
        print(f"  [retro] 시드 삽입됨: {retro_topic['topic']}")

    # 사용 시드 상태 갱신 + 역추적 기록
    selected_seed_ids = [t["seed_id"] for t in selected if t.get("source") == "retro"]
    if selected_seed_ids:
        mark_seeds_as_used(selected_seed_ids, tiktok_date=args.date)
        for t in selected:
            if t.get("source") == "retro":
                record_link(t["seed_id"], args.date, t.get("index", 0), t.get("topic", ""))

    schedule = generate_schedule(selected, args.date, config)

    save_schedule(schedule, output_dir)
    generate_plan_summary(selected, schedule, output_dir)

    print(f"[02_planning] 완료 — {len(selected)}개 영상 기획")


if __name__ == "__main__":
    main()
