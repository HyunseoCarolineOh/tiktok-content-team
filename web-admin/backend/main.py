"""
TikTok 콘텐츠 어드민 — FastAPI 앱.

개발: uvicorn main:app --reload --port 8000
프로덕션: npm run build → uvicorn main:app --port 8000
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers.pipeline import router as pipeline_router
from routers.outputs import router as outputs_router
from routers.schedule import router as schedule_router
from routers.upload import router as upload_router

app = FastAPI(
    title="TikTok 콘텐츠 어드민 API",
    description="파이프라인 제어 + 콘텐츠 검토 + 스케줄 관리",
    version="0.1.0",
)

# CORS — 개발 모드에서 Vite(5173) 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(pipeline_router)
app.include_router(outputs_router)
app.include_router(schedule_router)
app.include_router(upload_router)


# React SPA 정적 파일 서빙 (프로덕션)
STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    # /assets 등 정적 파일
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        """React SPA — 모든 미매칭 경로를 index.html로 fallback."""
        index = STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return FileResponse(str(STATIC_DIR / "index.html"))
