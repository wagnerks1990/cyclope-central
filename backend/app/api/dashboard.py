from fastapi import APIRouter, Depends
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.api.alerts import _alert_response
from app.api.schemas import DashboardSummaryResponse
from app.core.security import require_permission
from app.db.session import get_db
from app.models.alert import Alert
from app.models.device import Device
from app.models.user import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    current: User = Depends(require_permission("dashboard:read")), db: Session = Depends(get_db)
) -> DashboardSummaryResponse:
    total = (
        db.scalar(
            select(func.count())
            .select_from(Device)
            .where(Device.organization_id == current.organization_id)
        )
        or 0
    )
    online = (
        db.scalar(
            select(func.count())
            .select_from(Device)
            .where(Device.organization_id == current.organization_id, Device.is_online.is_(True))
        )
        or 0
    )
    offline = total - online
    warnings = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.organization_id == current.organization_id,
                Alert.status == "active",
                Alert.severity == "warning",
            )
        )
        or 0
    )
    critical = (
        db.scalar(
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.organization_id == current.organization_id,
                Alert.status == "active",
                Alert.severity == "critical",
            )
        )
        or 0
    )
    attention = (
        db.scalar(
            select(func.count(distinct(Alert.device_id))).where(
                Alert.organization_id == current.organization_id,
                Alert.status.in_(["active", "acknowledged"]),
            )
        )
        or 0
    )
    recent = db.scalars(
        select(Alert)
        .where(Alert.organization_id == current.organization_id)
        .order_by(Alert.last_seen_at.desc())
        .limit(10)
    ).all()
    return DashboardSummaryResponse(
        total_devices=total,
        online_devices=online,
        offline_devices=offline,
        active_warning_alerts=warnings,
        active_critical_alerts=critical,
        devices_needing_attention=attention,
        recent_alerts=[_alert_response(db, alert) for alert in recent],
    )
