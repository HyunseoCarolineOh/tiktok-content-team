"""
outputs/ 파일 CRUD 라우터.

GET    /api/outputs/dates                      → 날짜 목록
GET    /api/outputs/{date}/summary             → 날짜별 현황 요약
GET    /api/outputs/{date}/scripts             → 스크립트 목록
GET    /api/outputs/{date}/scripts/{filename}  → 스크립트 내용
PUT    /api/outputs/{date}/scripts/{filename}  → 스크립트 저장
GET    /api/outputs/{date}/metadata            → 메타데이터 목록
GET    /api/outputs/{date}/metadata/{filename} → 메타데이터 내용
PUT    /api/outputs/{date}/metadata/{filename} → 메타데이터 저장
POST   /api/outputs/{date}/raw                 → raw 영상 업로드
GET    /api/outputs/{date}/final               → 최종 영상 목록
"""

from fastapi import APIRouter, HTTPException, UploadFile
from pydantic import BaseModel

import services.file_service as fs

router = APIRouter(prefix="/api/outputs", tags=["outputs"])


class ScriptBody(BaseModel):
    content: str


class MetadataBody(BaseModel):
    data: dict


@router.get("/dates")
async def get_dates() -> dict:
    return {"dates": fs.list_dates()}


@router.get("/{date}/summary")
async def get_summary(date: str) -> dict:
    return fs.get_date_summary(date)


@router.get("/{date}/scripts")
async def get_scripts(date: str) -> dict:
    return {"scripts": fs.list_scripts(date)}


@router.get("/{date}/scripts/{filename}")
async def get_script(date: str, filename: str) -> dict:
    try:
        content = fs.read_script(date, filename)
        return {"filename": filename, "content": content}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/{date}/scripts/{filename}")
async def save_script(date: str, filename: str, body: ScriptBody) -> dict:
    try:
        fs.write_script(date, filename, body.content)
        return {"ok": True}
    except PermissionError as e:
        raise HTTPException(403, str(e))


@router.get("/{date}/metadata")
async def get_metadata_list(date: str) -> dict:
    return {"metadata": fs.list_metadata(date)}


@router.get("/{date}/metadata/{filename}")
async def get_metadata(date: str, filename: str) -> dict:
    try:
        data = fs.read_metadata(date, filename)
        return {"filename": filename, "data": data}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.put("/{date}/metadata/{filename}")
async def save_metadata(date: str, filename: str, body: MetadataBody) -> dict:
    try:
        fs.write_metadata(date, filename, body.data)
        return {"ok": True}
    except PermissionError as e:
        raise HTTPException(403, str(e))


@router.post("/{date}/raw")
async def upload_raw_video(date: str, file: UploadFile) -> dict:
    content = await file.read()
    filename = file.filename or "video.mp4"
    path = fs.save_raw_video(date, filename, content)
    return {"ok": True, "path": str(path), "size": len(content)}


@router.get("/{date}/final")
async def get_final_videos(date: str) -> dict:
    return {"videos": fs.list_final_videos(date)}
