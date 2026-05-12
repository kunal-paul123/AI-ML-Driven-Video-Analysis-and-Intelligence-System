"""
Video Analysis API
──────────────────
Single endpoint: POST /api/v1/video/analyze
Accepts a video file (or browser WebM), runs YOLOv8, returns detections.
"""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Query

from app.services.video_analyzer import analyze_video

router = APIRouter(prefix="/video", tags=["Video"])

UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm", ".webm"}


def _format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


@router.post("/analyze")
async def analyze_video_file(
    file: UploadFile = File(...),
    sample_fps: int = Query(default=2, ge=1, le=10, description="Frames per second to sample"),
    confidence: float = Query(default=0.35, ge=0.1, le=1.0, description="Detection confidence threshold"),
):
    """
    Upload a video file (or browser-recorded WebM) and run YOLOv8 object detection on it.
    Returns frame-by-frame detections and any security alerts triggered.
    """
    # ── Validate file extension ───────────────────────────────────────────────
    suffix = Path(file.filename or "video.webm").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # ── Save uploaded file ────────────────────────────────────────────────────
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{file_id}{suffix}"

    try:
        content = await file.read()
        save_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # ── Run YOLO analysis ─────────────────────────────────────────────────────
    try:
        result = analyze_video(
            video_path=str(save_path),
            sample_fps=sample_fps,
            confidence_threshold=confidence,
        )
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # ── Build alerts from detections ──────────────────────────────────────────
    WEAPON_CLASSES = {"knife", "scissors", "gun", "pistol", "rifle"}
    generated_alerts = []
    seen_alert_types: set[str] = set()

    for frame in result.detections:
        persons = [o for o in frame.objects if o["class"] == "person"]
        weapons = [o for o in frame.objects if o["class"] in WEAPON_CLASSES]

        # Armed person alert (person + weapon in same frame)
        if persons and weapons and "armed_person" not in seen_alert_types:
            seen_alert_types.add("armed_person")
            generated_alerts.append({
                "alert_type": "weapon_detected",
                "severity": "critical",
                "title": "Armed Person Detected",
                "description": f"A person was detected with a {weapons[0]['class']} at {_format_time(frame.timestamp_seconds)}.",
                "confidence": max(w["confidence"] for w in weapons),
                "frame_number": frame.frame_number,
            })

        # Weapon alone
        for obj in frame.objects:
            if obj["class"] in WEAPON_CLASSES:
                key = f"weapon_{obj['class']}"
                if key not in seen_alert_types:
                    seen_alert_types.add(key)
                    generated_alerts.append({
                        "alert_type": "weapon_detected",
                        "severity": "critical",
                        "title": f"{obj['class'].capitalize()} Detected",
                        "description": f"A {obj['class']} was detected at {_format_time(frame.timestamp_seconds)} with {obj['confidence']:.0%} confidence.",
                        "confidence": obj["confidence"],
                        "frame_number": frame.frame_number,
                    })

        # Crowd detection (5+ people in one frame)
        if len(persons) >= 5 and "crowd" not in seen_alert_types:
            seen_alert_types.add("crowd")
            generated_alerts.append({
                "alert_type": "crowd_surge",
                "severity": "high",
                "title": f"Crowd Detected — {len(persons)} People",
                "description": f"{len(persons)} people detected simultaneously at {_format_time(frame.timestamp_seconds)}.",
                "confidence": None,
                "frame_number": frame.frame_number,
            })

    # ── Build detections output ───────────────────────────────────────────────
    detections_output = [
        {
            "frame_number": fd.frame_number,
            "timestamp_seconds": fd.timestamp_seconds,
            "timestamp_formatted": _format_time(fd.timestamp_seconds),
            "objects_detected": len(fd.objects),
            "objects": fd.objects,
        }
        for fd in result.detections
    ]

    return {
        "file_id": file_id,
        "original_filename": file.filename,
        "analysis": {
            "duration_seconds": result.duration_seconds,
            "frames_analyzed": result.total_frames_processed,
            "frames_with_detections": len(result.detections),
            "unique_classes_detected": result.unique_classes,
            "detection_summary": result.summary,
        },
        "alerts_generated": generated_alerts,
        "alerts_count": len(generated_alerts),
        "detections": detections_output,
        "analyzed_at": datetime.utcnow().isoformat(),
    }
