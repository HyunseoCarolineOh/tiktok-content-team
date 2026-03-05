"""
파이프라인 공통 유틸리티 모듈.

모든 파이프라인 스크립트(01~06)에서 재사용.
"""

import json
import os
import sys
from pathlib import Path


def load_config(config_path: str = "config/config.json") -> dict:
    """config.json 로드."""
    path = Path(config_path)
    if not path.exists():
        print(f"오류: 설정 파일을 찾을 수 없습니다 — {config_path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def setup_output_dir(base_dir: str, date_str: str) -> Path:
    """outputs/{date}/ 폴더 생성 후 Path 반환."""
    output_dir = Path(base_dir) / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_agent_prompt(agent_name: str, agents_dir: str = "agents") -> str:
    """
    agents/{name}.md에서 시스템 프롬프트 섹션 추출.

    '## 시스템 프롬프트' 헤더 이후부터 다음 '##' 헤더 전까지의 내용을 반환.
    해당 섹션이 없으면 전체 파일 내용 반환.
    """
    path = Path(agents_dir) / f"{agent_name}.md"
    if not path.exists():
        print(f"경고: 에이전트 파일을 찾을 수 없습니다 — {path}", file=sys.stderr)
        return ""
    content = path.read_text(encoding="utf-8")

    # '## 시스템 프롬프트' 섹션 추출
    lines = content.splitlines()
    in_section = False
    section_lines = []
    for line in lines:
        if line.strip().startswith("## 시스템 프롬프트"):
            in_section = True
            continue
        if in_section:
            if line.startswith("## ") and not line.startswith("## 시스템 프롬프트"):
                break
            section_lines.append(line)

    if section_lines:
        return "\n".join(section_lines).strip()
    return content.strip()


def load_brand_guide(brand_path: str = "config/brand_guide.json") -> dict:
    """brand_guide.json 로드."""
    path = Path(brand_path)
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_env_or_fail(env_key: str) -> str:
    """환경변수를 가져오거나 실패 시 종료."""
    value = os.environ.get(env_key)
    if not value:
        print(f"오류: 환경변수 {env_key}가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)
    return value


def save_json(data: dict | list, path: Path, indent: int = 2) -> None:
    """JSON 파일 저장 (UTF-8)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(path: Path) -> dict | list:
    """JSON 파일 로드."""
    if not path.exists():
        print(f"오류: 파일을 찾을 수 없습니다 — {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)
