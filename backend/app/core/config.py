from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "VideoAI Surveillance System"
    app_version: str = "1.0.0"
    debug: bool = True
    environment: str = "development"

    # Database (Neon DB)
    database_url: str

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    frontend_url: str = "http://localhost:3000"

    # Video Processing
    max_concurrent_streams: int = 10
    frame_extraction_fps: int = 5
    max_video_file_size_mb: int = 500

    # ML Engine
    yolo_model_path: str = "../ml-engine/weights/yolov8n.pt"
    ml_confidence_threshold: float = 0.5
    ml_iou_threshold: float = 0.45

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings — reads .env once at startup."""
    return Settings()


settings = get_settings()
