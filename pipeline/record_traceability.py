"""
회고 시드 → TikTok 영상 역추적 레코드를 traceability.json에 기록하는 모듈.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

TRACE_PATH = Path("G:/내 드라이브/Claude-Workspace/Projects/shared-data/retro-seeds/traceability.json")
QUEUE_PATH = Path("G:/내 드라이브/Claude-Workspace/Projects/shared-data/retro-seeds/queue.json")


def record_link(
    seed_id: str,
    tiktok_date: str,
    video_index: int,
    topic: str,
    script_path: str = "",
    trace_path: Path = TRACE_PATH,
    queue_path: Path = QUEUE_PATH,
) -> None:
    """회고 시드와 TikTok 영상의 연결을 traceability.json에 기록."""
    # 큐에서 시드 원본 정보 조회
    seed: dict = {}
    if queue_path.exists():
        queue: list[dict] = json.loads(queue_path.read_text(encoding="utf-8"))
        seed = next((s for s in queue if s["seed_id"] == seed_id), {})

    records: list[dict] = []
    if trace_path.exists():
        records = json.loads(trace_path.read_text(encoding="utf-8"))

    records.append({
        "seed_id": seed_id,
        "retro_date": seed.get("retro_date", ""),
        "retro_section": seed.get("section", ""),
        "original_text": seed.get("original_text", ""),
        "tiktok_date": tiktok_date,
        "video_index": video_index,
        "topic": topic,
        "script_path": script_path,
        "linked_at": datetime.now(timezone.utc).isoformat(),
    })

    trace_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
