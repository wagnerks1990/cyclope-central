from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.schemas import DeviceInventoryPayload
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.device_inventory import DeviceInventory
from app.models.disk_inventory import DiskInventory
from app.models.installed_software import InstalledSoftware
from app.models.network_interface_inventory import NetworkInterfaceInventory
from app.models.security_status import SecurityStatus
from app.models.update_status import UpdateStatus


def upsert_inventory(
    db: Session, *, device: Device, payload: DeviceInventoryPayload, now: datetime
) -> None:
    """Store latest read-only inventory without copying large software lists into check-ins."""
    inventory = db.scalar(select(DeviceInventory).where(DeviceInventory.device_id == device.id))
    if inventory is None:
        inventory = DeviceInventory(
            device_id=device.id,
            organization_id=device.organization_id,
            hostname=device.hostname,
            operating_system=device.operating_system,
            inventory_refreshed_at=now,
        )
        db.add(inventory)

    inventory.hostname = device.hostname
    inventory.operating_system = device.operating_system
    inventory.os_version = payload.os_version
    inventory.os_build = payload.os_build
    inventory.architecture = device.architecture
    inventory.agent_version = device.agent_version
    inventory.cpu_model = payload.cpu_model
    inventory.cpu_cores = payload.cpu_cores
    inventory.memory_total_bytes = payload.memory_total_bytes
    inventory.bios_vendor = payload.bios_vendor
    inventory.bios_version = payload.bios_version
    inventory.system_manufacturer = payload.system_manufacturer
    inventory.system_model = payload.system_model
    inventory.inventory_refreshed_at = now

    db.execute(delete(DiskInventory).where(DiskInventory.device_id == device.id))
    for disk in payload.disks:
        db.add(
            DiskInventory(
                device_id=device.id,
                organization_id=device.organization_id,
                name=disk.name,
                filesystem=disk.filesystem,
                size_bytes=disk.size_bytes,
                free_bytes=disk.free_bytes,
            )
        )

    db.execute(
        delete(NetworkInterfaceInventory).where(NetworkInterfaceInventory.device_id == device.id)
    )
    for adapter in payload.network_interfaces:
        db.add(
            NetworkInterfaceInventory(
                device_id=device.id,
                organization_id=device.organization_id,
                name=adapter.name,
                mac_address=adapter.mac_address,
                ip_addresses=adapter.ip_addresses,
            )
        )

    db.execute(delete(InstalledSoftware).where(InstalledSoftware.device_id == device.id))
    for software in payload.installed_software:
        db.add(
            InstalledSoftware(
                device_id=device.id,
                organization_id=device.organization_id,
                name=software.name,
                version=software.version,
                publisher=software.publisher,
                installed_at=software.installed_at,
            )
        )

    if payload.security is not None:
        security = db.scalar(select(SecurityStatus).where(SecurityStatus.device_id == device.id))
        if security is None:
            security = SecurityStatus(
                device_id=device.id,
                organization_id=device.organization_id,
                refreshed_at=now,
            )
            db.add(security)
        security.antivirus_product = payload.security.antivirus_product
        security.antivirus_enabled = payload.security.antivirus_enabled
        security.antivirus_up_to_date = payload.security.antivirus_up_to_date
        security.defender_enabled = payload.security.defender_enabled
        security.firewall_enabled = payload.security.firewall_enabled
        security.details = payload.security.details
        security.refreshed_at = now

    if payload.updates is not None:
        updates = db.scalar(select(UpdateStatus).where(UpdateStatus.device_id == device.id))
        if updates is None:
            updates = UpdateStatus(
                device_id=device.id,
                organization_id=device.organization_id,
                refreshed_at=now,
            )
            db.add(updates)
        updates.pending_reboot = payload.updates.pending_reboot
        updates.update_status = payload.updates.update_status
        updates.last_update_check_at = payload.updates.last_update_check_at
        updates.details = payload.updates.details
        updates.refreshed_at = now

    db.add(
        AuditLog(
            organization_id=device.organization_id,
            action="inventory.updated",
            target_type="device",
            target_id=str(device.id),
            metadata_json={
                "disk_count": len(payload.disks),
                "network_interface_count": len(payload.network_interfaces),
                "software_count": len(payload.installed_software),
            },
        )
    )
