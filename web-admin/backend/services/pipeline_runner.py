"""
파이프라인 subprocess 실행 + WebSocket 로그 스트리밍 서비스.
"""

import asyncio
import subprocess
import sys
import uuid
from pathlib import Path
from typing import AsyncGenerator

# run_id → asyncio.Queue 매핑 (진행 중인 파이프라인 로그)
_active_runs: dict[str, asyncio.Queue] = {}

# 프로젝트 루트: services/pipeline_runner.py → services → backend → web-admin → tiktok-content-team
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()

STEP_SCRIPTS = {
    "1": "pipeline/01_research.py",
    "2": "pipeline/02_planning.py",
    "3": "pipeline/03_scripting.py",
    "4": "pipeline/04_editing.py",
    "5": "pipeline/05_upload.py",
    "6": "pipeline/06_analytics.py",
}


def create_run(step: str, extra_args: list[str] | None = None) -> str:
    """
    파이프라인 스텝 subprocess 실행 시작 후 run_id 반환.

    실행은 백그라운드 태스크로 진행되며,
    로그는 _active_runs[run_id] 큐에 쌓임.
    """
    run_id = str(uuid.uuid4())[:8]
    queue: asyncio.Queue = asyncio.Queue()
    _active_runs[run_id] = queue

    script = STEP_SCRIPTS.get(str(step))
    if not script:
        raise ValueError(f"알 수 없는 스텝: {step}")

    args = extra_args or []
    asyncio.create_task(_run_process(run_id, script, args, queue))
    return run_id


async def _run_process(
    run_id: str,
    script: str,
    extra_args: list[str],
    queue: asyncio.Queue,
) -> None:
    """subprocess 실행 + stdout/stderr를 큐에 push."""
    cmd = [sys.executable, "-X", "utf8", "-u", script] + extra_args
    try:
        loop = asyncio.get_event_loop()

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_ROOT),
        )

        def _read_output() -> None:
            assert proc.stdout is not None
            for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                loop.call_soon_threadsafe(queue.put_nowait, {"type": "log", "message": line})
            proc.wait()
            loop.call_soon_threadsafe(
                queue.put_nowait, {"type": "done", "exit_code": proc.returncode}
            )

        await loop.run_in_executor(None, _read_output)
    except Exception as exc:
        import traceback
        err_detail = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        await queue.put({"type": "error", "message": err_detail})
        await queue.put({"type": "done", "exit_code": -1})
    finally:
        # 완료 후 일정 시간(60초) 뒤 큐 제거
        await asyncio.sleep(60)
        _active_runs.pop(run_id, None)


async def stream_logs(run_id: str) -> AsyncGenerator[dict, None]:
    """
    run_id에 해당하는 큐에서 로그 메시지를 yield.

    done 이벤트가 오면 스트리밍 종료.
    """
    queue = _active_runs.get(run_id)
    if queue is None:
        yield {"type": "error", "message": f"run_id={run_id} 를 찾을 수 없습니다."}
        return

    while True:
        try:
            msg = await asyncio.wait_for(queue.get(), timeout=120.0)
            yield msg
            if msg.get("type") == "done":
                break
        except asyncio.TimeoutError:
            yield {"type": "error", "message": "타임아웃: 파이프라인 응답 없음"}
            break


def list_active_runs() -> list[str]:
    """현재 실행 중인 run_id 목록 반환."""
    return list(_active_runs.keys())
