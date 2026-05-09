import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models.alert import Alert, AlertStatus, AlertSeverity, AlertType
from app.schemas.alert import AlertCreate, AlertUpdate, AlertResponse, AlertListResponse

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = 1,
    page_size: int = 20,
    severity: AlertSeverity | None = None,
    alert_type: AlertType | None = None,
    status: AlertStatus | None = None,
    camera_id: uuid.UUID | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List alerts with filtering and pagination."""
    query = select(Alert)

    if severity:
        query = query.where(Alert.severity == severity)
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    if status:
        query = query.where(Alert.status == status)
    if camera_id:
        query = query.where(Alert.camera_id == camera_id)
    if from_date:
        query = query.where(Alert.detected_at >= from_date)
    if to_date:
        query = query.where(Alert.detected_at <= to_date)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    skip = (page - 1) * page_size
    query = query.order_by(desc(Alert.detected_at)).offset(skip).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    return AlertListResponse(total=total, page=page, page_size=page_size, alerts=alerts)


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    payload: AlertCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new alert (typically called by the ML engine)."""
    alert = Alert(**payload.model_dump())
    db.add(alert)
    await db.flush()
    await db.refresh(alert)
    return alert


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: uuid.UUID,
    payload: AlertUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge, resolve, or update an alert."""
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Auto-set timestamps for status changes
    if "status" in update_data:
        if update_data["status"] == AlertStatus.ACKNOWLEDGED:
            alert.acknowledged_at = datetime.utcnow()
        elif update_data["status"] == AlertStatus.RESOLVED:
            alert.resolved_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(alert, field, value)

    await db.flush()
    await db.refresh(alert)
    return alert


@router.get("/stats/summary")
async def alert_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregate alert counts grouped by severity."""
    result = await db.execute(
        select(Alert.severity, func.count().label("count"))
        .group_by(Alert.severity)
    )
    rows = result.all()
    return {"by_severity": {row.severity: row.count for row in rows}}
