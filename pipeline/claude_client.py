"""
Anthropic Claude API 래퍼.

모든 파이프라인 스크립트에서 재사용할 Claude API 클라이언트.
"""

import json
import os
from pathlib import Path
from typing import Generator, Optional

import anthropic

_CREDENTIALS_PATH = Path(r"G:\내 드라이브\Claude-Workspace\assistant-config\credentials\api-keys.json")


def _load_api_key_from_credentials() -> str | None:
    """credentials 파일에서 Anthropic API 키 로드."""
    try:
        data = json.loads(_CREDENTIALS_PATH.read_text(encoding="utf-8"))
        return data["keys"]["anthropic"]["api_key"] or None
    except Exception:
        return None


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or _load_api_key_from_credentials()
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY 환경변수가 설정되지 않았고, credentials 파일에서도 키를 찾을 수 없습니다."
        )
    return anthropic.Anthropic(api_key=api_key)


def call(
    system_prompt: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
    thinking_budget: Optional[int] = None,
) -> str:
    """
    단순 텍스트 응답 호출.

    반환값: 어시스턴트 응답 텍스트 (thinking 블록 제외)
    """
    client = _get_client()
    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    if thinking_budget:
        kwargs["thinking"] = {"type": "adaptive", "budget_tokens": thinking_budget}

    response = client.messages.create(**kwargs)

    # thinking 블록 제외하고 text 블록만 수집
    texts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(texts)


def call_streaming(
    system_prompt: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
) -> Generator[str, None, None]:
    """
    스트리밍 텍스트 응답 — 토큰 단위로 yield.

    사용 예:
        for chunk in call_streaming(system, user):
            print(chunk, end="", flush=True)
    """
    client = _get_client()
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def call_json(
    system_prompt: str,
    user_message: str,
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
    thinking_budget: Optional[int] = None,
) -> dict | list:
    """
    JSON 응답 호출. 응답에서 JSON 블록을 파싱하여 반환.

    응답 형식 지침은 user_message에 포함시켜야 함.
    """
    # JSON만 반환하도록 시스템 프롬프트에 지침 추가
    full_system = system_prompt + "\n\n반드시 순수 JSON만 반환하세요. 마크다운 코드 블록 없이."
    raw = call(full_system, user_message, model, max_tokens, thinking_budget)

    # ```json ... ``` 블록 제거
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    return json.loads(raw)
