import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.alert import AlertSeverity, AlertStatus, AlertType


class AlertCreate(BaseModel):
    camera_id: uuid.UUID
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str | None = None
    confidence: float | None = None
    detected_objects: list[dict] | None = None
    bounding_boxes: list[dict] | None = None
    snapshot_path: str | None = None
    frame_number: int | None = None
    detected_at: datetime


class AlertUpdate(BaseModel):
    status: AlertStatus | None = None
    description: str | None = None
    ai_summary: str | None = None


class AlertResponse(BaseModel):
    id: uuid.UUID
    camera_id: uuid.UUID
    alert_type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    title: str
    description: str | None
    ai_summary: str | None
    confidence: float | None
    detected_objects: list[dict] | None
    snapshot_path: str | None
    frame_number: int | None
    detected_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    alerts: list[AlertResponse]
