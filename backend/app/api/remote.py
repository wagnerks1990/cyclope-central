from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    RemoteAccessPayload,
    RemoteDeviceLinkResponse,
    RemoteLaunchResponse,
    RemoteProviderCreateRequest,
    RemoteProviderResponse,
    RemoteSessionAuditResponse,
)
from app.core.security import require_permission
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.remote_device_link import RemoteDeviceLink
from app.models.remote_provider_config import RemoteProviderConfig
from app.models.remote_session_audit import RemoteSessionAudit
from app.models.user import User

router = APIRouter(tags=["remote"])

PROVIDER_RUSTDESK_OSS = "rustdesk_oss"


def _now() -> datetime:
    return datetime.now(UTC)


def provider_response(provider: RemoteProviderConfig) -> RemoteProviderResponse:
    return RemoteProviderResponse(
        id=provider.id,
        organization_id=provider.organization_id,
        provider_type=provider.provider_type,
        name=provider.name,
        host=provider.host,
        relay_host=provider.relay_host,
        public_key=provider.public_key,
        enabled=provider.enabled,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def audit_response(audit: RemoteSessionAudit) -> RemoteSessionAuditResponse:
    return RemoteSessionAuditResponse(
        id=audit.id,
        organization_id=audit.organization_id,
        device_id=audit.device_id,
        provider_config_id=audit.provider_config_id,
        actor_user_id=audit.actor_user_id,
        provider_type=audit.provider_type,
        action=audit.action,
        launch_url=audit.launch_url,
        metadata_json=audit.metadata_json,
        created_at=audit.created_at,
    )


def _get_device_or_404(db: Session, device_id: UUID, organization_id: UUID) -> Device:
    device = db.get(Device, device_id)
    if device is None or device.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


def _default_provider(db: Session, organization_id: UUID) -> RemoteProviderConfig | None:
    return db.scalar(
        select(RemoteProviderConfig)
        .where(
            RemoteProviderConfig.organization_id == organization_id,
            RemoteProviderConfig.provider_type == PROVIDER_RUSTDESK_OSS,
            RemoteProviderConfig.enabled.is_(True),
        )
        .order_by(RemoteProviderConfig.created_at)
        .limit(1)
    )


def _remote_link_response(
    *,
    organization_id: UUID,
    device_id: UUID,
    link: RemoteDeviceLink | None,
    provider: RemoteProviderConfig | None,
) -> RemoteDeviceLinkResponse:
    return RemoteDeviceLinkResponse(
        id=link.id if link else None,
        organization_id=organization_id,
        device_id=device_id,
        provider_config_id=(link.provider_config_id if link else (provider.id if provider else None)),
        provider_type=PROVIDER_RUSTDESK_OSS,
        rustdesk_id=link.rustdesk_id if link else None,
        installed=link.installed if link else False,
        last_status=link.last_status if link else "unknown",
        last_reported_at=link.last_reported_at if link else None,
        provider=provider_response(provider) if provider else None,
    )


def upsert_rustdesk_status(
    db: Session,
    *,
    device: Device,
    payload: RemoteAccessPayload,
    now: datetime,
) -> None:
    """Persist the latest RustDesk OSS status reported by an authenticated agent."""
    if payload.provider_type != PROVIDER_RUSTDESK_OSS:
        return
    provider = _default_provider(db, device.organization_id)
    link = db.scalar(
        select(RemoteDeviceLink).where(
            RemoteDeviceLink.organization_id == device.organization_id,
            RemoteDeviceLink.device_id == device.id,
            RemoteDeviceLink.provider_type == PROVIDER_RUSTDESK_OSS,
        )
    )
    if link is None:
        link = RemoteDeviceLink(
            organization_id=device.organization_id,
            device_id=device.id,
            provider_type=PROVIDER_RUSTDESK_OSS,
        )
        db.add(link)
    link.provider_config_id = provider.id if provider else link.provider_config_id
    link.installed = payload.installed
    link.rustdesk_id = payload.device_id
    link.last_status = payload.status
    link.last_reported_at = now


@router.get("/remote/providers", response_model=list[RemoteProviderResponse])
def list_remote_providers(
    current: User = Depends(require_permission("remote:read")), db: Session = Depends(get_db)
) -> list[RemoteProviderResponse]:
    providers = db.scalars(
        select(RemoteProviderConfig)
        .where(RemoteProviderConfig.organization_id == current.organization_id)
        .order_by(RemoteProviderConfig.created_at)
    ).all()
    return [provider_response(provider) for provider in providers]


@router.post(
    "/remote/providers",
    response_model=RemoteProviderResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_remote_provider(
    payload: RemoteProviderCreateRequest,
    current: User = Depends(require_permission("remote:manage")),
    db: Session = Depends(get_db),
) -> RemoteProviderResponse:
    provider = RemoteProviderConfig(
        organization_id=current.organization_id,
        provider_type=payload.provider_type,
        name=payload.name,
        host=payload.host,
        relay_host=payload.relay_host,
        public_key=payload.public_key,
        enabled=payload.enabled,
    )
    db.add(provider)
    db.add(
        AuditLog(
            organization_id=current.organization_id,
            actor_user_id=current.id,
            action="remote.provider.created",
            target_type="remote_provider",
            target_id=None,
            metadata_json={"provider_type": payload.provider_type, "host": payload.host},
        )
    )
    db.commit()
    db.refresh(provider)
    return provider_response(provider)


@router.get("/devices/{device_id}/remote", response_model=RemoteDeviceLinkResponse)
def get_device_remote(
    device_id: UUID,
    current: User = Depends(require_permission("remote:read")),
    db: Session = Depends(get_db),
) -> RemoteDeviceLinkResponse:
    device = _get_device_or_404(db, device_id, current.organization_id)
    provider = _default_provider(db, current.organization_id)
    link = db.scalar(
        select(RemoteDeviceLink).where(
            RemoteDeviceLink.organization_id == current.organization_id,
            RemoteDeviceLink.device_id == device.id,
            RemoteDeviceLink.provider_type == PROVIDER_RUSTDESK_OSS,
        )
    )
    if link and link.provider_config_id:
        provider = db.get(RemoteProviderConfig, link.provider_config_id) or provider
    return _remote_link_response(
        organization_id=current.organization_id, device_id=device.id, link=link, provider=provider
    )


@router.post("/devices/{device_id}/remote/launch", response_model=RemoteLaunchResponse)
def launch_device_remote(
    device_id: UUID,
    current: User = Depends(require_permission("remote:launch")),
    db: Session = Depends(get_db),
) -> RemoteLaunchResponse:
    device = _get_device_or_404(db, device_id, current.organization_id)
    link = db.scalar(
        select(RemoteDeviceLink).where(
            RemoteDeviceLink.organization_id == current.organization_id,
            RemoteDeviceLink.device_id == device.id,
            RemoteDeviceLink.provider_type == PROVIDER_RUSTDESK_OSS,
        )
    )
    if link is None or not link.installed or not link.rustdesk_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="RustDesk device link not available"
        )
    provider = db.get(RemoteProviderConfig, link.provider_config_id) if link.provider_config_id else None
    launch_url = f"rustdesk://{link.rustdesk_id}"
    audit = RemoteSessionAudit(
        organization_id=current.organization_id,
        device_id=device.id,
        provider_config_id=provider.id if provider else None,
        actor_user_id=current.id,
        provider_type=PROVIDER_RUSTDESK_OSS,
        action="remote.launch",
        launch_url=launch_url,
        metadata_json={
            "hostname": device.hostname,
            "provider_type": PROVIDER_RUSTDESK_OSS,
            "rustdesk_id": link.rustdesk_id,
        },
        created_at=_now(),
    )
    db.add(audit)
    db.add(
        AuditLog(
            organization_id=current.organization_id,
            actor_user_id=current.id,
            action="remote.launch",
            target_type="device",
            target_id=str(device.id),
            metadata_json={"provider_type": PROVIDER_RUSTDESK_OSS, "rustdesk_id": link.rustdesk_id},
        )
    )
    db.commit()
    db.refresh(audit)
    return RemoteLaunchResponse(
        launch_url=launch_url,
        rustdesk_id=link.rustdesk_id,
        audit_id=audit.id,
        manual_instructions="If your browser blocks protocol launch, open RustDesk locally and connect to the listed RustDesk ID.",
    )


@router.get("/devices/{device_id}/remote/audit", response_model=list[RemoteSessionAuditResponse])
def list_device_remote_audit(
    device_id: UUID,
    current: User = Depends(require_permission("remote:read")),
    db: Session = Depends(get_db),
) -> list[RemoteSessionAuditResponse]:
    _get_device_or_404(db, device_id, current.organization_id)
    audits = db.scalars(
        select(RemoteSessionAudit)
        .where(
            RemoteSessionAudit.organization_id == current.organization_id,
            RemoteSessionAudit.device_id == device_id,
        )
        .order_by(desc(RemoteSessionAudit.created_at))
    ).all()
    return [audit_response(audit) for audit in audits]
