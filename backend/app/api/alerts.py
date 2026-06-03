from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.schemas import AlertEventResponse, AlertResponse
from app.db.session import get_db
from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.device import Device

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alert_response(db: Session, alert: Alert, include_events: bool = False) -> AlertResponse:
    device = db.get(Device, alert.device_id)
    rule = db.get(AlertRule, alert.rule_id)
    events = []
    if include_events:
        events = [
            AlertEventResponse(
                id=event.id,
                event_type=event.event_type,
                message=event.message,
                metadata_json=event.metadata_json,
                created_at=event.created_at,
            )
            for event in db.scalars(
                select(AlertEvent)
                .where(AlertEvent.alert_id == alert.id)
                .order_by(AlertEvent.created_at)
            )
        ]
    return AlertResponse(
        id=alert.id,
        organization_id=alert.organization_id,
        device_id=alert.device_id,
        rule_id=alert.rule_id,
        severity=alert.severity,
        status=alert.status,
        title=alert.title,
        message=alert.message,
        first_seen_at=alert.first_seen_at,
        last_seen_at=alert.last_seen_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        device_hostname=device.hostname if device else None,
        rule_key=rule.rule_key if rule else None,
        events=events,
    )


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    severity: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    device_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    query = select(Alert)
    if severity:
        query = query.where(Alert.severity == severity)
    if status_filter:
        query = query.where(Alert.status == status_filter)
    if device_id:
        query = query.where(Alert.device_id == device_id)
    alerts = db.scalars(query.order_by(desc(Alert.last_seen_at))).all()
    return [_alert_response(db, alert) for alert in alerts]


@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: UUID, db: Session = Depends(get_db)) -> AlertResponse:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return _alert_response(db, alert, include_events=True)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
def acknowledge_alert(alert_id: UUID, db: Session = Depends(get_db)) -> AlertResponse:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.status == "active":
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        alert.status = "acknowledged"
        alert.acknowledged_at = now
        db.add(
            AlertEvent(
                organization_id=alert.organization_id,
                alert_id=alert.id,
                event_type="acknowledged",
                message="Alert acknowledged by operator.",
                metadata_json={},
            )
        )
        db.commit()
    return _alert_response(db, alert, include_events=True)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
def resolve_alert(alert_id: UUID, db: Session = Depends(get_db)) -> AlertResponse:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    if alert.status != "resolved":
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        alert.status = "resolved"
        alert.resolved_at = now
        db.add(
            AlertEvent(
                organization_id=alert.organization_id,
                alert_id=alert.id,
                event_type="resolved",
                message="Alert resolved by operator.",
                metadata_json={},
            )
        )
        db.commit()
    return _alert_response(db, alert, include_events=True)
