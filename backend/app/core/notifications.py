import json
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from urllib import error, request
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.alert import Alert
from app.models.alert_rule import AlertRule
from app.models.audit_log import AuditLog
from app.models.notification_channel import NotificationChannel
from app.models.notification_delivery import NotificationDelivery
from app.models.notification_rule import NotificationRule

CHANNEL_TYPES = {"email", "webhook"}
DELIVERY_STATUSES = {"pending", "sent", "failed", "skipped"}
SECRET_MASK = "********"


def now_utc() -> datetime:
    return datetime.now(UTC)


def validate_channel_config(channel_type: str, config: dict) -> dict:
    if channel_type not in CHANNEL_TYPES:
        raise ValueError("Unsupported notification channel type")
    if channel_type == "email":
        recipients = config.get("recipients") or []
        if (
            not isinstance(recipients, list)
            or not recipients
            or not all(isinstance(r, str) for r in recipients)
        ):
            raise ValueError("Email channels require recipients")
        return {"recipients": recipients}
    url = str(config.get("url") or "")
    if not (url.startswith("https://") or url.startswith("http://")):
        raise ValueError("Webhook channels require an http(s) URL")
    headers = config.get("headers") or {}
    if not isinstance(headers, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in headers.items()
    ):
        raise ValueError("Webhook headers must be string key/value pairs")
    return {"url": url, "headers": headers}


def mask_channel_config(channel: NotificationChannel) -> dict:
    if channel.channel_type == "email":
        return {"recipients": channel.config.get("recipients", [])}
    headers = channel.config.get("headers", {})
    masked_headers = {key: SECRET_MASK for key in headers}
    return {"url": channel.config.get("url"), "headers": masked_headers}


def enqueue_alert_notifications(db: Session, alert: Alert) -> None:
    """Create pending deliveries for matching enabled notification rules.

    Called only when an alert is newly created, not for repeated detections or state transitions.
    """
    alert_rule = db.get(AlertRule, alert.rule_id)
    if alert_rule is None:
        return
    rules = db.scalars(
        select(NotificationRule).where(
            NotificationRule.organization_id == alert.organization_id,
            NotificationRule.enabled.is_(True),
        )
    ).all()
    for rule in rules:
        if rule.severity_filter and alert.severity not in rule.severity_filter:
            continue
        if rule.alert_rule_type_filter and alert_rule.rule_key not in rule.alert_rule_type_filter:
            continue
        for channel_id in rule.channel_ids:
            try:
                parsed_channel_id = UUID(str(channel_id))
            except ValueError:
                continue
            channel = _get_enabled_channel(db, alert.organization_id, channel_id)
            delivery = NotificationDelivery(
                organization_id=alert.organization_id,
                alert_id=alert.id,
                channel_id=parsed_channel_id,
                status="pending" if channel is not None else "skipped",
                attempts=0,
                last_error=None
                if channel is not None
                else "Notification channel missing or disabled.",
            )
            db.add(delivery)
            _audit(
                db,
                alert.organization_id,
                "notification.enqueued",
                "alert",
                str(alert.id),
                {"channel_id": str(channel_id), "status": delivery.status},
            )


def _get_enabled_channel(
    db: Session, organization_id: UUID, channel_id: str
) -> NotificationChannel | None:
    try:
        parsed = UUID(str(channel_id))
    except ValueError:
        return None
    channel = db.get(NotificationChannel, parsed)
    if channel is None or channel.organization_id != organization_id or not channel.enabled:
        return None
    return channel


def process_pending_deliveries(db: Session, *, limit: int = 25) -> list[NotificationDelivery]:
    deliveries = db.scalars(
        select(NotificationDelivery)
        .where(NotificationDelivery.status == "pending")
        .order_by(NotificationDelivery.created_at)
        .limit(limit)
    ).all()
    for delivery in deliveries:
        process_delivery(db, delivery)
    db.commit()
    return deliveries


def process_delivery(db: Session, delivery: NotificationDelivery) -> NotificationDelivery:
    if delivery.status != "pending":
        return delivery
    channel = db.get(NotificationChannel, delivery.channel_id)
    alert = db.get(Alert, delivery.alert_id)
    if channel is None or alert is None or not channel.enabled:
        delivery.status = "skipped"
        delivery.last_error = "Notification channel or alert unavailable."
        _audit(
            db,
            delivery.organization_id,
            "notification.skipped",
            "notification_delivery",
            str(delivery.id),
            {},
        )
        return delivery
    delivery.attempts += 1
    try:
        if channel.channel_type == "email":
            _send_email(channel, alert)
        elif channel.channel_type == "webhook":
            _send_webhook(channel, alert)
        else:
            raise ValueError("Unsupported notification channel type")
    except Exception as exc:  # noqa: BLE001 - failures must not break alert creation/delivery loop.
        delivery.last_error = _safe_error(exc)
        delivery.status = (
            "failed" if delivery.attempts >= settings.notification_retry_limit else "pending"
        )
        _audit(
            db,
            delivery.organization_id,
            "notification.failed",
            "notification_delivery",
            str(delivery.id),
            {"attempts": delivery.attempts},
        )
        return delivery
    delivery.status = "sent"
    delivery.sent_at = now_utc()
    delivery.last_error = None
    _audit(
        db,
        delivery.organization_id,
        "notification.sent",
        "notification_delivery",
        str(delivery.id),
        {"attempts": delivery.attempts},
    )
    return delivery


def build_webhook_payload(alert: Alert) -> dict:
    return {
        "event": "alert.created",
        "alert": {
            "id": str(alert.id),
            "organization_id": str(alert.organization_id),
            "device_id": str(alert.device_id),
            "rule_id": str(alert.rule_id),
            "severity": alert.severity,
            "status": alert.status,
            "title": alert.title,
            "message": alert.message,
            "first_seen_at": alert.first_seen_at.isoformat(),
            "last_seen_at": alert.last_seen_at.isoformat(),
        },
    }


def _send_webhook(channel: NotificationChannel, alert: Alert) -> None:
    body = json.dumps(build_webhook_payload(alert)).encode("utf-8")
    headers = {"Content-Type": "application/json", **channel.config.get("headers", {})}
    req = request.Request(channel.config["url"], data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=settings.notification_timeout_seconds) as response:
        if response.status >= 400:
            raise RuntimeError(f"Webhook returned HTTP {response.status}")


def _send_email(channel: NotificationChannel, alert: Alert) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from_email
    message["To"] = ", ".join(channel.config.get("recipients", []))
    message["Subject"] = f"[{alert.severity.upper()}] {alert.title}"
    message.set_content(f"{alert.title}\n\n{alert.message}\n\nAlert ID: {alert.id}")
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=settings.notification_timeout_seconds
    ) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, error.HTTPError):
        return f"HTTP error {exc.code}"
    if isinstance(exc, error.URLError):
        return "Webhook connection failed"
    return str(exc)[:512]


def _audit(
    db: Session,
    organization_id: UUID,
    action: str,
    target_type: str,
    target_id: str,
    metadata: dict,
) -> None:
    db.add(
        AuditLog(
            organization_id=organization_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_json=metadata,
        )
    )
