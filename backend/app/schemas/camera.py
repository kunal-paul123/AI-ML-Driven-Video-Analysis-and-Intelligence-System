import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator

from app.models.camera import CameraStatus, DeviceType, FeedType


# ── Request Schemas ────────────────────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    description: str | None = None
    location: str | None = None
    zone: str | None = None
    feed_url: str
    feed_type: FeedType = FeedType.RTSP
    device_type: DeviceType = DeviceType.CCTV
    latitude: float | None = None
    longitude: float | None = None


class CameraUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    location: str | None = None
    zone: str | None = None
    feed_url: str | None = None
    feed_type: FeedType | None = None
    device_type: DeviceType | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool | None = None


# ── Response Schemas ───────────────────────────────────────────────────────────

class CameraResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    location: str | None
    zone: str | None
    feed_url: str
    feed_type: FeedType
    device_type: DeviceType
    latitude: float | None
    longitude: float | None
    status: CameraStatus
    is_active: bool
    fps: int | None
    created_at: datetime
    updated_at: datetime
    last_seen_at: datetime | None

    model_config = {"from_attributes": True}


class CameraListResponse(BaseModel):
    total: int
    cameras: list[CameraResponse]
