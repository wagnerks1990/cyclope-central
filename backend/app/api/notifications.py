from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    NotificationChannelCreateRequest,
    NotificationChannelPatchRequest,
    NotificationChannelResponse,
    NotificationDeliveryResponse,
    NotificationRuleCreateRequest,
    NotificationRulePatchRequest,
    NotificationRuleResponse,
)
from app.core.alerts import ALERT_SEVERITIES
from app.core.notifications import mask_channel_config, validate_channel_config
from app.db.session import get_db
from app.models.notification_channel import NotificationChannel
from app.models.notification_delivery import NotificationDelivery
from app.models.notification_rule import NotificationRule
from app.models.organization import Organization

router = APIRouter(tags=["notifications"])


def channel_response(channel: NotificationChannel) -> NotificationChannelResponse:
    return NotificationChannelResponse(
        id=channel.id,
        organization_id=channel.organization_id,
        name=channel.name,
        channel_type=channel.channel_type,
        enabled=channel.enabled,
        config=mask_channel_config(channel),
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )


def rule_response(rule: NotificationRule) -> NotificationRuleResponse:
    return NotificationRuleResponse(
        id=rule.id,
        organization_id=rule.organization_id,
        name=rule.name,
        enabled=rule.enabled,
        severity_filter=rule.severity_filter,
        alert_rule_type_filter=rule.alert_rule_type_filter,
        channel_ids=[UUID(str(channel_id)) for channel_id in rule.channel_ids],
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def delivery_response(db: Session, delivery: NotificationDelivery) -> NotificationDeliveryResponse:
    channel = db.get(NotificationChannel, delivery.channel_id)
    return NotificationDeliveryResponse(
        id=delivery.id,
        organization_id=delivery.organization_id,
        alert_id=delivery.alert_id,
        channel_id=delivery.channel_id,
        channel_name=channel.name if channel else None,
        channel_type=channel.channel_type if channel else None,
        status=delivery.status,
        attempts=delivery.attempts,
        last_error=delivery.last_error,
        created_at=delivery.created_at,
        sent_at=delivery.sent_at,
    )


def _require_org(db: Session, organization_id: UUID) -> None:
    if db.get(Organization, organization_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")


def _validate_rule_filters(
    severities: list[str], channel_ids: list[UUID], db: Session, organization_id: UUID
) -> list[str]:
    invalid = [severity for severity in severities if severity not in ALERT_SEVERITIES]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid severity filter"
        )
    for channel_id in channel_ids:
        channel = db.get(NotificationChannel, channel_id)
        if channel is None or channel.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid notification channel"
            )
    return [str(channel_id) for channel_id in channel_ids]


@router.get("/notification-channels", response_model=list[NotificationChannelResponse])
def list_channels(
    organization_id: UUID | None = None, db: Session = Depends(get_db)
) -> list[NotificationChannelResponse]:
    query = select(NotificationChannel).order_by(desc(NotificationChannel.created_at))
    if organization_id is not None:
        query = query.where(NotificationChannel.organization_id == organization_id)
    return [channel_response(channel) for channel in db.scalars(query).all()]


@router.post(
    "/notification-channels",
    response_model=NotificationChannelResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_channel(
    payload: NotificationChannelCreateRequest, db: Session = Depends(get_db)
) -> NotificationChannelResponse:
    _require_org(db, payload.organization_id)
    try:
        config = validate_channel_config(payload.channel_type, payload.config)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    channel = NotificationChannel(
        organization_id=payload.organization_id,
        name=payload.name,
        channel_type=payload.channel_type,
        enabled=payload.enabled,
        config=config,
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)
    return channel_response(channel)


@router.patch("/notification-channels/{channel_id}", response_model=NotificationChannelResponse)
def patch_channel(
    channel_id: UUID, payload: NotificationChannelPatchRequest, db: Session = Depends(get_db)
) -> NotificationChannelResponse:
    channel = db.get(NotificationChannel, channel_id)
    if channel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification channel not found"
        )
    if payload.name is not None:
        channel.name = payload.name
    if payload.enabled is not None:
        channel.enabled = payload.enabled
    if payload.config is not None:
        try:
            channel.config = validate_channel_config(channel.channel_type, payload.config)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(channel)
    return channel_response(channel)


@router.get("/notification-rules", response_model=list[NotificationRuleResponse])
def list_rules(
    organization_id: UUID | None = None, db: Session = Depends(get_db)
) -> list[NotificationRuleResponse]:
    query = select(NotificationRule).order_by(desc(NotificationRule.created_at))
    if organization_id is not None:
        query = query.where(NotificationRule.organization_id == organization_id)
    return [rule_response(rule) for rule in db.scalars(query).all()]


@router.post(
    "/notification-rules",
    response_model=NotificationRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_rule(
    payload: NotificationRuleCreateRequest, db: Session = Depends(get_db)
) -> NotificationRuleResponse:
    _require_org(db, payload.organization_id)
    channel_ids = _validate_rule_filters(
        payload.severity_filter, payload.channel_ids, db, payload.organization_id
    )
    rule = NotificationRule(
        organization_id=payload.organization_id,
        name=payload.name,
        enabled=payload.enabled,
        severity_filter=payload.severity_filter,
        alert_rule_type_filter=payload.alert_rule_type_filter,
        channel_ids=channel_ids,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule_response(rule)


@router.patch("/notification-rules/{rule_id}", response_model=NotificationRuleResponse)
def patch_rule(
    rule_id: UUID, payload: NotificationRulePatchRequest, db: Session = Depends(get_db)
) -> NotificationRuleResponse:
    rule = db.get(NotificationRule, rule_id)
    if rule is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification rule not found"
        )
    severities = (
        payload.severity_filter if payload.severity_filter is not None else rule.severity_filter
    )
    channels = (
        payload.channel_ids
        if payload.channel_ids is not None
        else [UUID(str(channel_id)) for channel_id in rule.channel_ids]
    )
    channel_ids = _validate_rule_filters(severities, channels, db, rule.organization_id)
    if payload.name is not None:
        rule.name = payload.name
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    if payload.severity_filter is not None:
        rule.severity_filter = payload.severity_filter
    if payload.alert_rule_type_filter is not None:
        rule.alert_rule_type_filter = payload.alert_rule_type_filter
    if payload.channel_ids is not None:
        rule.channel_ids = channel_ids
    db.commit()
    db.refresh(rule)
    return rule_response(rule)


@router.get("/notifications/deliveries", response_model=list[NotificationDeliveryResponse])
def list_deliveries(
    organization_id: UUID | None = None, db: Session = Depends(get_db)
) -> list[NotificationDeliveryResponse]:
    query = select(NotificationDelivery).order_by(desc(NotificationDelivery.created_at)).limit(100)
    if organization_id is not None:
        query = query.where(NotificationDelivery.organization_id == organization_id)
    return [delivery_response(db, delivery) for delivery in db.scalars(query).all()]
