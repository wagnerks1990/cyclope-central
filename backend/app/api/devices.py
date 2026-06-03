from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.alerts import _alert_response
from app.api.schemas import (
    AlertResponse,
    CheckinSummary,
    DeviceDetail,
    DeviceInventoryResponse,
    DeviceSummary,
    DiskInventoryResponse,
    InstalledSoftwareResponse,
    NetworkInterfaceInventoryResponse,
    SecurityStatusResponse,
    SoftwareInventoryResponse,
    UpdateStatusResponse,
)
from app.core.config import settings
from app.core.security import require_permission
from app.db.session import get_db
from app.models.alert import Alert
from app.models.device import Device
from app.models.device_checkin import DeviceCheckin
from app.models.device_inventory import DeviceInventory
from app.models.disk_inventory import DiskInventory
from app.models.installed_software import InstalledSoftware
from app.models.network_interface_inventory import NetworkInterfaceInventory
from app.models.security_status import SecurityStatus
from app.models.update_status import UpdateStatus
from app.models.user import User

router = APIRouter(prefix="/devices", tags=["devices"])


def _is_online(device: Device) -> bool:
    if device.last_seen_at is None:
        return False
    last_seen = device.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=UTC)
    return last_seen >= datetime.now(UTC) - timedelta(seconds=settings.device_offline_after_seconds)


def _sync_status(device: Device) -> None:
    online = _is_online(device)
    device.is_online = online
    device.status = "online" if online else "offline"


def _summary(device: Device) -> DeviceSummary:
    online = device.is_online
    return DeviceSummary(
        id=device.id,
        hostname=device.hostname,
        operating_system=device.operating_system,
        architecture=device.architecture,
        ip_address=device.ip_address,
        agent_version=device.agent_version,
        health_status=device.health_status,
        status="online" if online else "offline",
        is_online=online,
        last_seen_at=device.last_seen_at,
    )


def _get_device_or_404(db: Session, device_id: UUID, organization_id: UUID) -> Device:
    device = db.get(Device, device_id)
    if device is None or device.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


@router.get("", response_model=list[DeviceSummary])
def list_devices(
    current: User = Depends(require_permission("devices:read")), db: Session = Depends(get_db)
) -> list[DeviceSummary]:
    """Return enrolled devices for dashboard inventory views."""
    devices = db.scalars(
        select(Device)
        .where(Device.organization_id == current.organization_id)
        .order_by(Device.hostname)
    ).all()
    for device in devices:
        _sync_status(device)
    db.commit()
    return [_summary(device) for device in devices]


@router.get("/{device_id}", response_model=DeviceDetail)
def get_device(
    device_id: UUID,
    current: User = Depends(require_permission("devices:read")),
    db: Session = Depends(get_db),
) -> DeviceDetail:
    """Return a single device with latest check-in telemetry."""
    device = _get_device_or_404(db, device_id, current.organization_id)
    _sync_status(device)
    db.commit()
    latest = db.scalar(
        select(DeviceCheckin)
        .where(DeviceCheckin.device_id == device_id)
        .order_by(desc(DeviceCheckin.checked_in_at))
        .limit(1)
    )
    summary = _summary(device).model_dump()
    return DeviceDetail(
        **summary,
        machine_identifier=device.machine_identifier,
        latest_checkin=(
            CheckinSummary(
                checked_in_at=latest.checked_in_at,
                status=latest.status,
                ip_address=latest.ip_address,
                agent_version=latest.agent_version,
                payload=latest.payload,
            )
            if latest
            else None
        ),
    )


@router.get("/{device_id}/inventory", response_model=DeviceInventoryResponse)
def get_device_inventory(
    device_id: UUID,
    current: User = Depends(require_permission("devices:read")),
    db: Session = Depends(get_db),
) -> DeviceInventoryResponse:
    """Return latest hardware, disk, and network inventory for a device."""
    _get_device_or_404(db, device_id, current.organization_id)
    inventory = db.scalar(select(DeviceInventory).where(DeviceInventory.device_id == device_id))
    if inventory is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory not found")
    disks = db.scalars(select(DiskInventory).where(DiskInventory.device_id == device_id)).all()
    network_interfaces = db.scalars(
        select(NetworkInterfaceInventory).where(NetworkInterfaceInventory.device_id == device_id)
    ).all()
    return DeviceInventoryResponse(
        device_id=inventory.device_id,
        hostname=inventory.hostname,
        operating_system=inventory.operating_system,
        os_version=inventory.os_version,
        os_build=inventory.os_build,
        architecture=inventory.architecture,
        agent_version=inventory.agent_version,
        cpu_model=inventory.cpu_model,
        cpu_cores=inventory.cpu_cores,
        memory_total_bytes=inventory.memory_total_bytes,
        bios_vendor=inventory.bios_vendor,
        bios_version=inventory.bios_version,
        system_manufacturer=inventory.system_manufacturer,
        system_model=inventory.system_model,
        inventory_refreshed_at=inventory.inventory_refreshed_at,
        disks=[
            DiskInventoryResponse(
                id=disk.id,
                name=disk.name,
                filesystem=disk.filesystem,
                size_bytes=disk.size_bytes,
                free_bytes=disk.free_bytes,
            )
            for disk in disks
        ],
        network_interfaces=[
            NetworkInterfaceInventoryResponse(
                id=adapter.id,
                name=adapter.name,
                mac_address=adapter.mac_address,
                ip_addresses=adapter.ip_addresses,
            )
            for adapter in network_interfaces
        ],
    )


@router.get("/{device_id}/software", response_model=SoftwareInventoryResponse)
def get_device_software(
    device_id: UUID,
    current: User = Depends(require_permission("devices:read")),
    db: Session = Depends(get_db),
) -> SoftwareInventoryResponse:
    """Return latest installed software inventory for a device."""
    _get_device_or_404(db, device_id, current.organization_id)
    inventory = db.scalar(select(DeviceInventory).where(DeviceInventory.device_id == device_id))
    software = db.scalars(
        select(InstalledSoftware)
        .where(InstalledSoftware.device_id == device_id)
        .order_by(InstalledSoftware.name)
    ).all()
    return SoftwareInventoryResponse(
        device_id=device_id,
        inventory_refreshed_at=inventory.inventory_refreshed_at if inventory else None,
        software=[
            InstalledSoftwareResponse(
                id=item.id,
                name=item.name,
                version=item.version,
                publisher=item.publisher,
                installed_at=item.installed_at,
            )
            for item in software
        ],
    )


@router.get("/{device_id}/security", response_model=SecurityStatusResponse)
def get_device_security(
    device_id: UUID,
    current: User = Depends(require_permission("devices:read")),
    db: Session = Depends(get_db),
) -> SecurityStatusResponse:
    """Return latest endpoint security posture for a device."""
    _get_device_or_404(db, device_id, current.organization_id)
    security_row = db.scalar(select(SecurityStatus).where(SecurityStatus.device_id == device_id))
    if security_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Security status not found"
        )
    return SecurityStatusResponse(
        device_id=device_id,
        antivirus_product=security_row.antivirus_product,
        antivirus_enabled=security_row.antivirus_enabled,
        antivirus_up_to_date=security_row.antivirus_up_to_date,
        defender_enabled=security_row.defender_enabled,
        firewall_enabled=security_row.firewall_enabled,
        details=security_row.details,
        refreshed_at=security_row.refreshed_at,
    )


@router.get("/{device_id}/updates", response_model=UpdateStatusResponse)
def get_device_updates(
    device_id: UUID,
    current: User = Depends(require_permission("devices:read")),
    db: Session = Depends(get_db),
) -> UpdateStatusResponse:
    """Return latest update and pending reboot posture for a device."""
    _get_device_or_404(db, device_id, current.organization_id)
    update_row = db.scalar(select(UpdateStatus).where(UpdateStatus.device_id == device_id))
    if update_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Update status not found")
    return UpdateStatusResponse(
        device_id=device_id,
        pending_reboot=update_row.pending_reboot,
        update_status=update_row.update_status,
        last_update_check_at=update_row.last_update_check_at,
        details=update_row.details,
        refreshed_at=update_row.refreshed_at,
    )


@router.get("/{device_id}/alerts", response_model=list[AlertResponse])
def get_device_alerts(
    device_id: UUID,
    current: User = Depends(require_permission("alerts:read")),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    """Return active and historical alerts for a device."""
    _get_device_or_404(db, device_id, current.organization_id)
    alerts = db.scalars(
        select(Alert)
        .where(Alert.device_id == device_id, Alert.organization_id == current.organization_id)
        .order_by(desc(Alert.last_seen_at))
    ).all()
    return [_alert_response(db, alert) for alert in alerts]
