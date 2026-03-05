"""
스케줄 조회/수정 라우터.

GET /api/schedule/{date}     → schedule.json 조회
PUT /api/schedule/{date}     → schedule.json 전체 저장
PATCH /api/schedule/{date}/{video_index} → 특정 영상 발행 시간 변경
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import services.file_service as fs

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class ScheduleBody(BaseModel):
    schedule: dict


class VideoUpdateBody(BaseModel):
    publish_at: Optional[str] = None
    topic: Optional[str] = None
    category: Optional[str] = None


@router.get("/{date}")
async def get_schedule(date: str) -> dict:
    schedule = fs.read_schedule(date)
    if schedule is None:
        raise HTTPException(404, f"{date} 날짜의 schedule.json이 없습니다.")
    return {"schedule": schedule}


@router.put("/{date}")
async def save_schedule(date: str, body: ScheduleBody) -> dict:
    fs.write_schedule(date, body.schedule)
    return {"ok": True}


@router.patch("/{date}/{video_index}")
async def update_video_schedule(date: str, video_index: int, body: VideoUpdateBody) -> dict:
    schedule = fs.read_schedule(date)
    if schedule is None:
        raise HTTPException(404, f"{date} 날짜의 schedule.json이 없습니다.")

    videos = schedule.get("videos", [])
    target = next((v for v in videos if v.get("index") == video_index), None)
    if target is None:
        raise HTTPException(404, f"영상 인덱스 {video_index}를 찾을 수 없습니다.")

    if body.publish_at is not None:
        target["publish_at"] = body.publish_at
    if body.topic is not None:
        target["topic"] = body.topic
    if body.category is not None:
        target["category"] = body.category

    fs.write_schedule(date, schedule)
    return {"ok": True, "updated": target}
