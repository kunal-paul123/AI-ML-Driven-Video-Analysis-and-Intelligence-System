import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Enum, DateTime, Float, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AlertSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, enum.Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    FALSE_POSITIVE = "false_positive"


class AlertType(str, enum.Enum):
    WEAPON_DETECTED = "weapon_detected"
    LOITERING = "loitering"
    INTRUSION = "intrusion"
    CROWD_SURGE = "crowd_surge"
    FIGHTING = "fighting"
    FALLEN_PERSON = "fallen_person"
    SUSPICIOUS_ITEM = "suspicious_item"
    UNAUTHORIZED_VEHICLE = "unauthorized_vehicle"
    ANOMALY = "anomaly"
    CUSTOM = "custom"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Relationships
    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)

    # Alert Details
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), default=AlertStatus.OPEN)

    # Description
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # LLM-generated summary

    # Detection metadata
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_objects: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # [{"class": "person", "confidence": 0.95}]
    bounding_boxes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Evidence
    snapshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Path in MinIO or local
    video_clip_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    frame_number: Mapped[int | None] = mapped_column(nullable=True)

    # Timestamps
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Alert id={self.id} type={self.alert_type} severity={self.severity}>"
