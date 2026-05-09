import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Float, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Detection(Base):
    """
    Individual object detection event from a single frame.
    High-volume table — consider TimescaleDB hypertable for this in production.
    """
    __tablename__ = "detections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cameras.id"), nullable=False)

    # Object details
    object_class: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "person", "weapon"
    track_id: Mapped[int | None] = mapped_column(Integer, nullable=True)     # ByteTrack ID
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Bounding box: [x1, y1, x2, y2] normalized 0-1
    bbox: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Frame info
    frame_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Behavior / extra metadata
    extra: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # pose data, zone info, etc.

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Detection id={self.id} class={self.object_class} conf={self.confidence:.2f}>"
