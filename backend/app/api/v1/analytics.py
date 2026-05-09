from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.alert import Alert, AlertSeverity
from app.models.detection import Detection
from app.models.camera import Camera

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/timeline")
async def alert_timeline(
    hours: int = 24,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns alert counts grouped by hour for the last N hours.
    Used to power the timeline chart on the dashboard.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(
            func.date_trunc("hour", Alert.detected_at).label("hour"),
            func.count().label("count"),
            Alert.severity,
        )
        .where(Alert.detected_at >= since)
        .group_by("hour", Alert.severity)
        .order_by("hour")
    )
    rows = result.all()
    return {
        "hours": hours,
        "data": [
            {"hour": row.hour.isoformat(), "count": row.count, "severity": row.severity}
            for row in rows
        ],
    }


@router.get("/heatmap/{camera_id}")
async def activity_heatmap(
    camera_id: str,
    hours: int = 6,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns bounding box centroids for a camera to render a heatmap.
    Frontend aggregates these into a density heatmap overlay.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(Detection.bbox, Detection.object_class, Detection.detected_at)
        .where(Detection.camera_id == camera_id)
        .where(Detection.detected_at >= since)
        .limit(5000)
    )
    rows = result.all()
    points = []
    for row in rows:
        bbox = row.bbox
        if bbox and len(bbox) == 4:
            cx = (bbox[0] + bbox[2]) / 2
            cy = (bbox[1] + bbox[3]) / 2
            points.append({"x": cx, "y": cy, "class": row.object_class})

    return {"camera_id": camera_id, "hours": hours, "points": points, "total": len(points)}


@router.get("/overview")
async def system_overview(db: AsyncSession = Depends(get_db)):
    """High-level system stats for the dashboard overview cards."""
    camera_count = await db.execute(select(func.count()).select_from(Camera))
    alert_count = await db.execute(select(func.count()).select_from(Alert))
    detection_count = await db.execute(select(func.count()).select_from(Detection))
    critical_count = await db.execute(
        select(func.count()).select_from(Alert).where(Alert.severity == AlertSeverity.CRITICAL)
    )

    return {
        "total_cameras": camera_count.scalar_one(),
        "total_alerts": alert_count.scalar_one(),
        "total_detections": detection_count.scalar_one(),
        "critical_alerts": critical_count.scalar_one(),
    }
