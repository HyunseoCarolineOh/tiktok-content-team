"""
retro-seeds 큐에서 pending 시드를 로드하고,
02_planning.py의 topics_pool 포맷으로 변환하는 모듈.

Claude API 없음 — 순수 파일 I/O + 규칙 기반.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

QUEUE_PATH = Path("G:/내 드라이브/Claude-Workspace/Projects/shared-data/retro-seeds/queue.json")


def load_pending_seeds(queue_path: Path = QUEUE_PATH, max_seeds: int = 3) -> list[dict]:
    """pending 상태 시드를 relevance_score 높은 순으로 최대 max_seeds개 반환."""
    if not queue_path.exists():
        return []
    queue: list[dict] = json.loads(queue_path.read_text(encoding="utf-8"))
    pending = [s for s in queue if s.get("status") == "pending"]
    pending.sort(key=lambda s: s.get("relevance_score", 0), reverse=True)
    return pending[:max_seeds]


def seed_to_topic(seed: dict) -> dict:
    """시드 → 02_planning.py의 topics_pool 호환 포맷 변환."""
    return {
        "topic": seed["tiktok_angle"][:15],
        "angle": seed["tiktok_angle"],
        "keywords": ["자기계발", "성장", seed.get("growth_category", "")],
        "score": 21,
        "priority": "high",
        "source": "retro",
        "seed_id": seed["seed_id"],
        "retro_date": seed["retro_date"],
        "original_text": seed["original_text"],
        "hook_direction": seed["tiktok_hook_direction"],
        "category": "개인성장",
    }


def mark_seeds_as_used(
    seed_ids: list[str],
    queue_path: Path = QUEUE_PATH,
    tiktok_date: str = "",
) -> None:
    """지정 seed_id 목록의 status → 'used', used_at → tiktok_date 또는 현재시각."""
    if not queue_path.exists():
        return
    queue: list[dict] = json.loads(queue_path.read_text(encoding="utf-8"))
    used_at = tiktok_date or datetime.now(timezone.utc).isoformat()
    for seed in queue:
        if seed["seed_id"] in seed_ids:
            seed["status"] = "used"
            seed["used_at"] = used_at
    queue_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
