"""
outputs/ 디렉토리 파일 CRUD 서비스.
"""

import json
import shutil
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def list_dates() -> list[str]:
    """outputs/ 하위 날짜 폴더 목록 (최신순)."""
    if not OUTPUTS_DIR.exists():
        return []
    dates = sorted(
        [d.name for d in OUTPUTS_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")],
        reverse=True,
    )
    return dates


def list_scripts(date: str) -> list[dict]:
    """outputs/{date}/scripts/ 파일 목록."""
    scripts_dir = OUTPUTS_DIR / date / "scripts"
    if not scripts_dir.exists():
        return []
    return [
        {"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime}
        for f in sorted(scripts_dir.glob("*.txt"))
    ]


def list_metadata(date: str) -> list[dict]:
    """outputs/{date}/metadata/ 파일 목록."""
    meta_dir = OUTPUTS_DIR / date / "metadata"
    if not meta_dir.exists():
        return []
    return [
        {"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime}
        for f in sorted(meta_dir.glob("*.json"))
    ]


def list_final_videos(date: str) -> list[dict]:
    """outputs/{date}/final/ 영상 파일 목록."""
    final_dir = OUTPUTS_DIR / date / "final"
    if not final_dir.exists():
        return []
    return [
        {"name": f.name, "size": f.stat().st_size, "modified": f.stat().st_mtime}
        for f in sorted(final_dir.glob("*.mp4"))
    ]


def read_script(date: str, filename: str) -> str:
    """스크립트 파일 내용 읽기."""
    path = OUTPUTS_DIR / date / "scripts" / filename
    _check_path_safe(path)
    if not path.exists():
        raise FileNotFoundError(f"스크립트 파일 없음: {filename}")
    return path.read_text(encoding="utf-8")


def write_script(date: str, filename: str, content: str) -> None:
    """스크립트 파일 저장."""
    scripts_dir = OUTPUTS_DIR / date / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    path = scripts_dir / filename
    _check_path_safe(path)
    path.write_text(content, encoding="utf-8")


def read_metadata(date: str, filename: str) -> dict:
    """메타데이터 JSON 읽기."""
    path = OUTPUTS_DIR / date / "metadata" / filename
    _check_path_safe(path)
    if not path.exists():
        raise FileNotFoundError(f"메타데이터 파일 없음: {filename}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_metadata(date: str, filename: str, data: dict) -> None:
    """메타데이터 JSON 저장."""
    meta_dir = OUTPUTS_DIR / date / "metadata"
    meta_dir.mkdir(parents=True, exist_ok=True)
    path = meta_dir / filename
    _check_path_safe(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def read_schedule(date: str) -> Optional[dict]:
    """schedule.json 읽기. 없으면 None 반환."""
    path = OUTPUTS_DIR / date / "schedule.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_schedule(date: str, data: dict) -> None:
    """schedule.json 저장."""
    date_dir = OUTPUTS_DIR / date
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / "schedule.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_raw_video(date: str, filename: str, content: bytes) -> Path:
    """raw 영상 파일 저장."""
    raw_dir = OUTPUTS_DIR / date / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / filename
    _check_path_safe(path)
    path.write_bytes(content)
    return path


def get_date_summary(date: str) -> dict:
    """특정 날짜의 콘텐츠 현황 요약."""
    date_dir = OUTPUTS_DIR / date
    return {
        "date": date,
        "has_topics": (date_dir / "topics_pool.json").exists(),
        "has_schedule": (date_dir / "schedule.json").exists(),
        "scripts_count": len(list(( date_dir / "scripts").glob("*.txt"))) if (date_dir / "scripts").exists() else 0,
        "metadata_count": len(list((date_dir / "metadata").glob("*.json"))) if (date_dir / "metadata").exists() else 0,
        "raw_videos_count": len(list((date_dir / "raw").glob("*.mp4"))) if (date_dir / "raw").exists() else 0,
        "final_videos_count": len(list((date_dir / "final").glob("*_edited.mp4"))) if (date_dir / "final").exists() else 0,
        "has_report": (date_dir / "report.md").exists(),
    }


def _check_path_safe(path: Path) -> None:
    """경로 traversal 방지: outputs/ 외부 접근 차단."""
    try:
        path.resolve().relative_to(OUTPUTS_DIR.resolve())
    except ValueError:
        raise PermissionError(f"허용되지 않은 경로: {path}")
