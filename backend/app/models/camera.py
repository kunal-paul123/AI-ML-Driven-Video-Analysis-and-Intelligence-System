import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Enum, DateTime, Float, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CameraStatus(str, enum.Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"
    UNKNOWN = "unknown"


class FeedType(str, enum.Enum):
    RTSP = "rtsp"
    RTMP = "rtmp"
    FILE = "file"
    WEBCAM = "webcam"
    HTTP = "http"


class DeviceType(str, enum.Enum):
    CCTV = "cctv"
    DRONE = "drone"
    BODY_CAM = "body_cam"
    ROBOT = "robot"
    MOBILE = "mobile"


class Camera(Base):
    __tablename__ = "cameras"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Connection
    feed_url: Mapped[str] = mapped_column(String(500), nullable=False)
    feed_type: Mapped[FeedType] = mapped_column(Enum(FeedType), default=FeedType.RTSP)
    device_type: Mapped[DeviceType] = mapped_column(Enum(DeviceType), default=DeviceType.CCTV)

    # Geographic coordinates
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[CameraStatus] = mapped_column(Enum(CameraStatus), default=CameraStatus.UNKNOWN)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    fps: Mapped[int | None] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Camera id={self.id} name={self.name} status={self.status}>"
