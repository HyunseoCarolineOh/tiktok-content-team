"""
TikTok OAuth + 업로드 라우터.

GET  /api/upload/auth/url    → OAuth 인증 URL 반환
GET  /callback               → OAuth code → token 교환 (TikTok redirect_uri)
GET  /api/upload/auth/status → 토큰 캐시 유무 확인
POST /api/upload/video       → 특정 영상 TikTok 업로드 실행 (파이프라인 5단계 호출)
"""

import json
import os
import secrets
import hashlib
import base64
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter(tags=["upload"])

PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
TOKEN_CACHE_PATH = PROJECT_ROOT / "config" / ".tiktok_token.json"


def _load_tiktok_config() -> dict:
    config_path = PROJECT_ROOT / "config" / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)["tiktok"]


def _load_cached_token() -> Optional[dict]:
    if TOKEN_CACHE_PATH.exists():
        with open(TOKEN_CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)
    return None


def _save_token(token_data: dict) -> None:
    TOKEN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=2)


# PKCE state/verifier 임시 저장 (단일 사용자 로컬 용도)
_pkce_state: dict = {}


@router.get("/api/upload/auth/url")
async def get_auth_url() -> dict:
    """TikTok OAuth 2.0 PKCE 인증 URL 생성."""
    cfg = _load_tiktok_config()
    client_key = os.environ.get(cfg["client_key_env"], "")
    if not client_key:
        raise HTTPException(400, "TIKTOK_CLIENT_KEY 환경변수가 설정되지 않았습니다.")

    # PKCE: code_verifier + code_challenge
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    _pkce_state["verifier"] = code_verifier
    _pkce_state["state"] = state

    scopes = ",".join(cfg["scopes"])
    redirect_uri = "http://localhost:8000/callback"
    auth_url = (
        f"https://www.tiktok.com/v2/auth/authorize/"
        f"?client_key={client_key}"
        f"&scope={scopes}"
        f"&response_type=code"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&code_challenge={code_challenge}"
        f"&code_challenge_method=S256"
    )
    return {"auth_url": auth_url}


@router.get("/callback", response_class=HTMLResponse)
async def tiktok_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
) -> str:
    """TikTok OAuth callback — code를 access_token으로 교환."""
    if error:
        return f"<h2>TikTok 인증 실패: {error}</h2>"

    if not code:
        return "<h2>오류: code 파라미터 없음</h2>"

    if state != _pkce_state.get("state"):
        return "<h2>오류: state 불일치 (CSRF 방어)</h2>"

    cfg = _load_tiktok_config()
    client_key = os.environ.get(cfg["client_key_env"], "")
    client_secret = os.environ.get(cfg["client_secret_env"], "")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data={
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "http://localhost:8000/callback",
                "code_verifier": _pkce_state.get("verifier", ""),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        return f"<h2>토큰 교환 실패: {resp.text}</h2>"

    token_data = resp.json()
    _save_token(token_data)
    _pkce_state.clear()

    return """
    <html><body style="font-family:sans-serif;text-align:center;margin-top:100px">
    <h2>✅ TikTok 인증 완료!</h2>
    <p>이 창을 닫고 어드민으로 돌아가세요.</p>
    <script>setTimeout(() => window.close(), 3000);</script>
    </body></html>
    """


@router.get("/api/upload/auth/status")
async def get_auth_status() -> dict:
    """TikTok 토큰 캐시 유무 확인."""
    token = _load_cached_token()
    return {
        "authenticated": token is not None,
        "has_token": token is not None,
    }


class UploadRequest(BaseModel):
    date: str
    video_index: Optional[int] = None
    dry_run: bool = False


@router.post("/api/upload/video")
async def upload_video(req: UploadRequest) -> dict:
    """
    05_upload.py를 subprocess로 실행하여 TikTok 업로드.
    실행 결과는 WebSocket 로그 스트리밍으로 확인.
    """
    from services.pipeline_runner import create_run

    extra_args = ["--date", req.date]
    if req.video_index is not None:
        extra_args += ["--index", str(req.video_index)]
    if req.dry_run:
        extra_args.append("--dry-run")

    run_id = create_run("5", extra_args)
    return {"run_id": run_id, "status": "started"}
