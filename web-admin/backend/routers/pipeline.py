"""
파이프라인 실행 + WebSocket 로그 스트리밍 라우터.

POST /api/pipeline/run/{step}   → 파이프라인 스텝 실행, run_id 반환
WS   /api/pipeline/ws/logs/{run_id} → 실시간 로그 스트리밍
GET  /api/pipeline/status       → 실행 중인 run 목록
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from services.pipeline_runner import create_run, list_active_runs, stream_logs

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run/{step}")
async def run_pipeline_step(
    step: str,
    date: Optional[str] = Query(None, description="실행 날짜 (YYYY-MM-DD)"),
    index: Optional[int] = Query(None, description="특정 영상 인덱스 (03/04/05용)"),
    mock: bool = Query(False, description="mock 데이터 사용 (06_analytics용)"),
    dry_run: bool = Query(False, description="dry-run 모드 (05_upload용)"),
    skip_whisper: bool = Query(False, description="Whisper 단계 건너뜀 (04_editing용)"),
) -> dict:
    """
    파이프라인 스텝 비동기 실행.

    step: "1" ~ "6"
    반환: {"run_id": "abc12345"}
    """
    extra_args = []
    if date:
        extra_args += ["--date", date]
    if index is not None:
        extra_args += ["--index", str(index)]
    if mock:
        extra_args.append("--mock")
    if dry_run:
        extra_args.append("--dry-run")
    if skip_whisper:
        extra_args.append("--skip-whisper")

    run_id = create_run(step, extra_args)
    return {"run_id": run_id, "step": step, "status": "started"}


@router.websocket("/ws/logs/{run_id}")
async def websocket_logs(websocket: WebSocket, run_id: str) -> None:
    """
    WebSocket으로 파이프라인 로그 실시간 스트리밍.

    메시지 형식:
    - {"type": "log", "message": "..."}
    - {"type": "done", "exit_code": 0}
    - {"type": "error", "message": "..."}
    """
    await websocket.accept()
    try:
        async for msg in stream_logs(run_id):
            await websocket.send_json(msg)
            if msg.get("type") == "done":
                break
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/status")
async def get_pipeline_status() -> dict:
    """현재 실행 중인 파이프라인 run 목록."""
    return {"active_runs": list_active_runs()}
