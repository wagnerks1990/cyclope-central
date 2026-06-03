from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.notifications import enqueue_alert_notifications
from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.device import Device
from app.models.device_inventory import DeviceInventory
from app.models.disk_inventory import DiskInventory
from app.models.security_status import SecurityStatus
from app.models.update_status import UpdateStatus

ALERT_SEVERITIES = {"info", "warning", "critical"}
ALERT_STATUSES = {"active", "acknowledged", "resolved"}


@dataclass(frozen=True)
class RuleDefinition:
    key: str
    name: str
    severity: str
    description: str
    parameters: dict


@dataclass(frozen=True)
class RuleResult:
    active: bool
    title: str
    message: str
    metadata: dict


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def default_rule_definitions() -> list[RuleDefinition]:
    return [
        RuleDefinition(
            "device_offline",
            "Device offline",
            "critical",
            "Device has not checked in within the configured window.",
            {"offline_minutes": settings.alert_device_offline_minutes},
        ),
        RuleDefinition(
            "low_disk_free_space",
            "Low disk free space",
            "warning",
            "A disk is below the configured free-space percentage.",
            {"free_percent": settings.alert_low_disk_free_percent},
        ),
        RuleDefinition(
            "high_memory_usage",
            "High memory usage",
            "warning",
            "Memory usage reported by the agent exceeds the configured percentage.",
            {"used_percent": settings.alert_high_memory_percent},
        ),
        RuleDefinition(
            "defender_disabled",
            "Windows Defender disabled",
            "critical",
            "Windows Defender is reported disabled.",
            {},
        ),
        RuleDefinition(
            "firewall_disabled",
            "Firewall disabled",
            "critical",
            "Endpoint firewall is reported disabled.",
            {},
        ),
        RuleDefinition(
            "pending_reboot",
            "Pending reboot",
            "warning",
            "Endpoint reports a pending reboot.",
            {},
        ),
        RuleDefinition(
            "windows_updates_stale",
            "Windows updates stale",
            "warning",
            "Windows update status is stale or reports stale updates.",
            {"stale_days": settings.alert_windows_update_stale_days},
        ),
        RuleDefinition(
            "agent_version_outdated",
            "Agent version outdated",
            "warning",
            "Agent version differs from the configured current version.",
            {"current_version": settings.current_agent_version},
        ),
        RuleDefinition(
            "inventory_not_refreshed",
            "Inventory not refreshed recently",
            "warning",
            "Latest inventory refresh is older than the configured window.",
            {"stale_hours": settings.alert_inventory_stale_hours},
        ),
    ]


def ensure_default_alert_rules(db: Session, organization_id: UUID) -> dict[str, AlertRule]:
    existing = {
        rule.rule_key: rule
        for rule in db.scalars(
            select(AlertRule).where(AlertRule.organization_id == organization_id)
        )
    }
    for definition in default_rule_definitions():
        if definition.key in existing:
            continue
        rule = AlertRule(
            organization_id=organization_id,
            rule_key=definition.key,
            name=definition.name,
            severity=definition.severity,
            description=definition.description,
            enabled=True,
            parameters=definition.parameters,
        )
        db.add(rule)
        db.flush()
        existing[rule.rule_key] = rule
    return existing


def evaluate_device_alerts(
    db: Session, *, device: Device, checkin_payload: dict | None = None, now: datetime | None = None
) -> None:
    """Evaluate deterministic read-only alert rules for a single device."""
    now = now or _now()
    rules = ensure_default_alert_rules(db, device.organization_id)
    inventory = db.scalar(select(DeviceInventory).where(DeviceInventory.device_id == device.id))
    disks = db.scalars(select(DiskInventory).where(DiskInventory.device_id == device.id)).all()
    security = db.scalar(select(SecurityStatus).where(SecurityStatus.device_id == device.id))
    updates = db.scalar(select(UpdateStatus).where(UpdateStatus.device_id == device.id))

    results = {
        "device_offline": _eval_offline(device, rules["device_offline"], now),
        "low_disk_free_space": _eval_low_disk(disks, rules["low_disk_free_space"]),
        "high_memory_usage": _eval_high_memory(checkin_payload or {}, rules["high_memory_usage"]),
        "defender_disabled": _eval_bool_false(
            security.defender_enabled if security else None,
            "Windows Defender disabled",
            "Windows Defender is disabled or unhealthy.",
        ),
        "firewall_disabled": _eval_bool_false(
            security.firewall_enabled if security else None,
            "Firewall disabled",
            "Endpoint firewall is disabled.",
        ),
        "pending_reboot": _eval_bool_true(
            updates.pending_reboot if updates else None,
            "Pending reboot",
            "Endpoint reports a pending reboot.",
        ),
        "windows_updates_stale": _eval_updates_stale(updates, rules["windows_updates_stale"], now),
        "agent_version_outdated": _eval_agent_version(device, rules["agent_version_outdated"]),
        "inventory_not_refreshed": _eval_inventory_stale(
            inventory, rules["inventory_not_refreshed"], now
        ),
    }
    for key, result in results.items():
        rule = rules[key]
        if rule.enabled:
            _apply_result(db, device=device, rule=rule, result=result, now=now)


def _eval_offline(device: Device, rule: AlertRule, now: datetime) -> RuleResult:
    minutes = int(rule.parameters.get("offline_minutes", settings.alert_device_offline_minutes))
    last_seen = _aware(device.last_seen_at)
    active = last_seen is None or last_seen < now - timedelta(minutes=minutes)
    return RuleResult(
        active,
        "Device offline",
        f"{device.hostname} has not checked in within {minutes} minutes.",
        {"offline_minutes": minutes, "last_seen_at": str(device.last_seen_at)},
    )


def _eval_low_disk(disks: list[DiskInventory], rule: AlertRule) -> RuleResult:
    threshold = float(rule.parameters.get("free_percent", settings.alert_low_disk_free_percent))
    low = []
    for disk in disks:
        if not disk.size_bytes or disk.free_bytes is None or disk.size_bytes <= 0:
            continue
        free_percent = (disk.free_bytes / disk.size_bytes) * 100
        if free_percent < threshold:
            low.append({"name": disk.name, "free_percent": round(free_percent, 2)})
    return RuleResult(
        bool(low),
        "Low disk free space",
        f"{len(low)} disk(s) are below {threshold}% free space.",
        {"threshold_percent": threshold, "disks": low},
    )


def _eval_high_memory(payload: dict, rule: AlertRule) -> RuleResult:
    threshold = float(rule.parameters.get("used_percent", settings.alert_high_memory_percent))
    total = payload.get("memory_total_bytes")
    used = payload.get("memory_used_bytes")
    active = bool(total and used is not None and total > 0 and (used / total) * 100 > threshold)
    percent = round((used / total) * 100, 2) if total and used is not None and total > 0 else None
    return RuleResult(
        active,
        "High memory usage",
        (
            f"Memory usage is {percent}% and exceeds {threshold}%."
            if percent
            else "Memory usage high."
        ),
        {"used_percent": percent, "threshold_percent": threshold},
    )


def _eval_bool_false(value: bool | None, title: str, message: str) -> RuleResult:
    return RuleResult(value is False, title, message, {"reported_value": value})


def _eval_bool_true(value: bool | None, title: str, message: str) -> RuleResult:
    return RuleResult(value is True, title, message, {"reported_value": value})


def _eval_updates_stale(updates: UpdateStatus | None, rule: AlertRule, now: datetime) -> RuleResult:
    days = int(rule.parameters.get("stale_days", settings.alert_windows_update_stale_days))
    if updates is None:
        return RuleResult(False, "Windows updates stale", "No update status reported.", {})
    last_check = _aware(updates.last_update_check_at)
    explicit_stale = updates.update_status in {"stale", "updates_stale"}
    stale_by_time = last_check is not None and last_check < now - timedelta(days=days)
    return RuleResult(
        explicit_stale or stale_by_time,
        "Windows updates stale",
        f"Windows update status is stale for more than {days} days.",
        {"stale_days": days, "update_status": updates.update_status},
    )


def _eval_agent_version(device: Device, rule: AlertRule) -> RuleResult:
    current = str(rule.parameters.get("current_version", settings.current_agent_version))
    active = bool(device.agent_version and device.agent_version != current)
    return RuleResult(
        active,
        "Agent version outdated",
        f"Agent version {device.agent_version or 'unknown'} is not {current}.",
        {"current_version": current, "agent_version": device.agent_version},
    )


def _eval_inventory_stale(
    inventory: DeviceInventory | None, rule: AlertRule, now: datetime
) -> RuleResult:
    hours = int(rule.parameters.get("stale_hours", settings.alert_inventory_stale_hours))
    refreshed = _aware(inventory.inventory_refreshed_at if inventory else None)
    active = refreshed is None or refreshed < now - timedelta(hours=hours)
    return RuleResult(
        active,
        "Inventory not refreshed recently",
        f"Inventory has not refreshed within {hours} hours.",
        {"stale_hours": hours, "inventory_refreshed_at": str(refreshed)},
    )


def _apply_result(
    db: Session, *, device: Device, rule: AlertRule, result: RuleResult, now: datetime
) -> None:
    alert = db.scalar(
        select(Alert).where(
            Alert.device_id == device.id,
            Alert.rule_id == rule.id,
            Alert.status.in_(["active", "acknowledged"]),
        )
    )
    if result.active:
        if alert is None:
            alert = Alert(
                organization_id=device.organization_id,
                device_id=device.id,
                rule_id=rule.id,
                severity=rule.severity,
                status="active",
                title=result.title,
                message=result.message,
                first_seen_at=now,
                last_seen_at=now,
            )
            db.add(alert)
            db.flush()
            _event(db, alert, "created", result.message, result.metadata)
            enqueue_alert_notifications(db, alert)
        else:
            alert.last_seen_at = now
            alert.message = result.message
            _event(db, alert, "repeated", result.message, result.metadata)
    elif alert is not None:
        alert.status = "resolved"
        alert.resolved_at = now
        alert.last_seen_at = now
        _event(db, alert, "resolved", "Alert condition cleared automatically.", result.metadata)


def _event(db: Session, alert: Alert, event_type: str, message: str, metadata: dict) -> None:
    db.add(
        AlertEvent(
            organization_id=alert.organization_id,
            alert_id=alert.id,
            event_type=event_type,
            message=message,
            metadata_json=metadata,
        )
    )
