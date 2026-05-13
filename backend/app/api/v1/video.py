"""
Video Analysis API
──────────────────
POST /api/v1/video/analyze  — Upload video, run YOLOv8, save alerts to DB, send SMS
GET  /api/v1/video/alerts   — Fetch past alerts from DB
"""
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.services.video_analyzer import analyze_video
from app.services.notification_service import send_sms_alert
from app.models.alert_history import AlertHistory
from app.database import get_db

router = APIRouter(prefix="/video", tags=["Video"])

UPLOAD_DIR = Path("app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
WEAPON_CLASSES = {"knife", "scissors", "gun", "pistol", "rifle"}


def _format_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# POST /analyze — Main AI analysis endpoint
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/analyze")
async def analyze_video_file(
    file: UploadFile = File(...),
    sample_fps: int = Query(default=2, ge=1, le=10),
    confidence: float = Query(default=0.35, ge=0.1, le=1.0),
    db: AsyncSession = Depends(get_db),
):
    # ── Validate extension ────────────────────────────────────────────────────
    suffix = Path(file.filename or "video.webm").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}'")

    # ── Save uploaded file ────────────────────────────────────────────────────
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{file_id}{suffix}"
    content = await file.read()
    save_path.write_bytes(content)

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
    generated_alerts = []
    seen_alert_types: set[str] = set()

    # Pre-collect all available screenshot paths in chronological order
    all_screenshots = [fd.screenshot_path for fd in result.detections if fd.screenshot_path]

    def get_context_screenshots(current_path: str | None) -> str | None:
        if not current_path or current_path not in all_screenshots:
            return current_path
        
        idx = all_screenshots.index(current_path)
        # Grab the triggering frame + up to 3 subsequent/previous frames to give context
        # Let's take the current, and up to 3 following frames (if available), else previous.
        start = max(0, idx - 1)
        end = min(len(all_screenshots), start + 4)
        context_paths = all_screenshots[start:end]
        return ",".join(context_paths)


    for frame in result.detections:
        persons = [o for o in frame.objects if o["class"] == "person"]
        weapons = [o for o in frame.objects if o["class"] in WEAPON_CLASSES]

        context_paths = get_context_screenshots(frame.screenshot_path)

        # Armed person (person + weapon in same frame)
        if persons and weapons and "armed_person" not in seen_alert_types:
            seen_alert_types.add("armed_person")
            generated_alerts.append({
                "alert_type": "weapon_detected",
                "severity": "critical",
                "title": "Armed Person Detected",
                "description": f"Person detected with a {weapons[0]['class']} at {_format_time(frame.timestamp_seconds)}.",
                "confidence": max(w["confidence"] for w in weapons),
                "frame_number": frame.frame_number,
                "screenshot_path": context_paths,
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
                        "description": f"A {obj['class']} detected at {_format_time(frame.timestamp_seconds)} with {obj['confidence']:.0%} confidence.",
                        "confidence": obj["confidence"],
                        "frame_number": frame.frame_number,
                        "screenshot_path": context_paths,
                    })

        # Crowd (5+ people)
        if len(persons) >= 5 and "crowd" not in seen_alert_types:
            seen_alert_types.add("crowd")
            generated_alerts.append({
                "alert_type": "crowd_surge",
                "severity": "high",
                "title": f"Crowd Detected — {len(persons)} People",
                "description": f"{len(persons)} people detected simultaneously at {_format_time(frame.timestamp_seconds)}.",
                "confidence": None,
                "frame_number": frame.frame_number,
                "screenshot_path": context_paths,
            })

    # ── Re-ID: Generate alerts for repeat/frequent persons ────────────────────
    registry = result.person_registry
    tracked_persons = registry.to_summary() if registry else []

    if registry:
        for person in registry.get_alert_persons():
            alert_key = f"frequent_person_{person.person_id}"
            if alert_key not in seen_alert_types:
                seen_alert_types.add(alert_key)
                generated_alerts.append({
                    "alert_type": "frequent_person",
                    "severity": "high",
                    "title": f"Frequent Person Detected — {person.person_id}",
                    "description": (
                        f"Person {person.person_id} has been spotted {person.sighting_count} times "
                        f"across this video (first at {_format_time(person.first_seen_timestamp)}, "
                        f"last at {_format_time(person.last_seen_timestamp)})."
                    ),
                    "confidence": 0.85,
                    "frame_number": person.last_seen_frame,
                    "screenshot_path": person.best_screenshot,
                })

        for person in registry.get_repeat_persons():
            if person.sighting_count < 4:  # Only yellow-level (not already red-alerted)
                alert_key = f"repeat_person_{person.person_id}"
                if alert_key not in seen_alert_types:
                    seen_alert_types.add(alert_key)
                    generated_alerts.append({
                        "alert_type": "repeat_person",
                        "severity": "medium",
                        "title": f"Repeat Person — {person.person_id}",
                        "description": (
                            f"Person {person.person_id} has appeared {person.sighting_count} times. "
                            f"First seen at {_format_time(person.first_seen_timestamp)}."
                        ),
                        "confidence": 0.75,
                        "frame_number": person.last_seen_frame,
                        "screenshot_path": person.best_screenshot,
                    })

    # ── Save alerts to DB + Send SMS ──────────────────────────────────────────
    saved_alerts = []
    for alert in generated_alerts:
        # 1. Send SMS first to get notification status
        notified = send_sms_alert(
            title=alert["title"],
            description=alert["description"],
            severity=alert["severity"],
        )

        # 2. Save to Neon PostgreSQL
        db_alert = AlertHistory(
            timestamp=datetime.utcnow(),
            alert_type=alert["alert_type"],
            severity=alert["severity"],
            title=alert["title"],
            description=alert["description"],
            confidence=alert["confidence"],
            frame_number=alert["frame_number"],
            screenshot_path=alert.get("screenshot_path"),
            notified=notified,
        )
        db.add(db_alert)
        await db.flush()  # Get the ID before commit

        saved_alerts.append({
            **alert,
            "id": db_alert.id,
            "notified": notified,
            "timestamp": db_alert.timestamp.isoformat() + "Z",
            "screenshot_url": f"http://localhost:8000/static/screenshots/{alert['screenshot_path']}" if alert.get("screenshot_path") else None
        })

    await db.commit()

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

    # ── Summarize Re-ID stats ─────────────────────────────────────────────────
    reid_summary = None
    if registry:
        all_persons = registry.get_all_persons()
        reid_summary = {
            "total_unique_persons": len(all_persons),
            "repeat_persons": len(registry.get_repeat_persons()),
            "frequent_persons": len(registry.get_alert_persons()),
        }

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
        "alerts_generated": saved_alerts,
        "alerts_count": len(saved_alerts),
        "detections": detections_output,
        "tracked_persons": tracked_persons,
        "reid_summary": reid_summary,
        "analyzed_at": datetime.utcnow().isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /alerts — Fetch past alerts from DB
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/alerts")
async def get_alert_history(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Fetch the most recent alerts from the database."""
    result = await db.execute(
        select(AlertHistory)
        .order_by(desc(AlertHistory.timestamp))
        .limit(limit)
    )
    alerts = result.scalars().all()

    def make_urls(paths_str: str | None) -> list[str]:
        if not paths_str:
            return []
        return [f"http://localhost:8000/static/screenshots/{p.strip()}" for p in paths_str.split(",") if p.strip()]

    return {
        "total": len(alerts),
        "alerts": [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat() + "Z",
                "alert_type": a.alert_type,
                "severity": a.severity,
                "title": a.title,
                "description": a.description,
                "confidence": a.confidence,
                "frame_number": a.frame_number,
                "screenshot_urls": make_urls(a.screenshot_path),
                "notified": a.notified,
            }
            for a in alerts
        ],
    }
