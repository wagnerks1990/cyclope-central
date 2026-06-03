from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.inventory import upsert_inventory
from app.api.remote import upsert_rustdesk_status
from app.api.jobs import job_response
from app.api.schemas import (
    AgentCheckinRequest,
    AgentCheckinResponse,
    AgentEnrollRequest,
    AgentEnrollResponse,
    AgentJobCompleteRequest,
    AgentJobPollRequest,
    AgentJobResponse,
)
from app.core.alerts import evaluate_device_alerts
from app.core.jobs import assign_jobs_for_agent, complete_job, start_job
from app.core.token_hashing import generate_secret, hash_token, verify_token
from app.db.session import get_db
from app.models.agent import Agent
from app.models.agent_job import AgentJob
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.device_checkin import DeviceCheckin
from app.models.enrollment_token import EnrollmentToken

router = APIRouter(prefix="/agent", tags=["agent"])


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _audit(
    db: Session,
    *,
    organization_id,
    action: str,
    target_type: str,
    target_id: str | None,
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


@router.post("/enroll", response_model=AgentEnrollResponse, status_code=status.HTTP_201_CREATED)
def enroll_agent(
    payload: AgentEnrollRequest, request: Request, db: Session = Depends(get_db)
) -> AgentEnrollResponse:
    """Enroll an endpoint using a limited-use organization enrollment token."""
    token_hash = hash_token(payload.enrollment_token)
    enrollment_token = db.scalar(
        select(EnrollmentToken).where(EnrollmentToken.token_hash == token_hash).with_for_update()
    )
    now = _now()
    if (
        enrollment_token is None
        or enrollment_token.revoked_at is not None
        or _aware(enrollment_token.expires_at) <= now
        or enrollment_token.uses >= enrollment_token.max_uses
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid enrollment token"
        )

    device = db.scalar(
        select(Device).where(
            Device.organization_id == enrollment_token.organization_id,
            Device.machine_identifier == payload.machine_identifier,
        )
    )
    if device is None:
        device = Device(
            organization_id=enrollment_token.organization_id,
            machine_identifier=payload.machine_identifier,
            hostname=payload.hostname,
            operating_system=payload.operating_system,
            architecture=payload.architecture,
            agent_version=payload.agent_version,
            ip_address=request.client.host if request.client else None,
            status="online",
            is_online=True,
            health_status="enrolled",
            last_seen_at=now,
        )
        db.add(device)
        db.flush()
    else:
        device.hostname = payload.hostname
        device.operating_system = payload.operating_system
        device.architecture = payload.architecture
        device.agent_version = payload.agent_version
        device.ip_address = request.client.host if request.client else device.ip_address
        device.status = "online"
        device.is_online = True
        device.health_status = "enrolled"
        device.last_seen_at = now

    device_secret = generate_secret()
    agent = db.scalar(select(Agent).where(Agent.install_id == payload.machine_identifier))
    if agent is None:
        agent = Agent(
            organization_id=enrollment_token.organization_id,
            device_id=device.id,
            install_id=payload.machine_identifier,
            version=payload.agent_version,
            device_secret_hash=hash_token(device_secret),
            last_seen_at=now,
        )
        db.add(agent)
    else:
        agent.organization_id = enrollment_token.organization_id
        agent.device_id = device.id
        agent.version = payload.agent_version
        agent.device_secret_hash = hash_token(device_secret)
        agent.last_seen_at = now

    enrollment_token.uses += 1
    _audit(
        db,
        organization_id=enrollment_token.organization_id,
        action="agent.enrolled",
        target_type="device",
        target_id=str(device.id),
        metadata={"hostname": payload.hostname, "agent_version": payload.agent_version},
    )
    db.commit()
    return AgentEnrollResponse(device_id=device.id, device_secret=device_secret)


@router.post("/checkin", response_model=AgentCheckinResponse)
def checkin_agent(
    payload: AgentCheckinRequest, request: Request, db: Session = Depends(get_db)
) -> AgentCheckinResponse:
    """Authenticate an enrolled device and persist a check-in telemetry envelope."""
    agent = db.scalar(select(Agent).where(Agent.device_id == payload.device_id))
    if agent is None or not verify_token(payload.device_secret, agent.device_secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials"
        )

    device = db.get(Device, payload.device_id)
    if device is None or device.organization_id != agent.organization_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials"
        )

    now = _now()
    ip_address = payload.ip_address or (request.client.host if request.client else None)
    device.hostname = payload.hostname
    device.operating_system = payload.operating_system
    device.architecture = payload.architecture
    device.ip_address = ip_address
    device.agent_version = payload.agent_version
    device.health_status = payload.health_status
    device.status = "online"
    device.is_online = True
    device.last_seen_at = now
    agent.version = payload.agent_version
    agent.last_seen_at = now

    checkin_payload = {
        "local_ips": payload.local_ips,
        "uptime_seconds": payload.uptime_seconds,
        "cpu_count": payload.cpu_count,
        "memory_total_bytes": payload.memory_total_bytes,
        "architecture": payload.architecture,
        "inventory_refreshed": payload.inventory is not None,
        "remote_access_reported": payload.remote_access is not None,
    }

    checkin = DeviceCheckin(
        organization_id=device.organization_id,
        device_id=device.id,
        agent_id=agent.id,
        status=payload.health_status,
        ip_address=ip_address,
        agent_version=payload.agent_version,
        payload=checkin_payload,
    )
    db.add(checkin)
    if payload.inventory is not None:
        upsert_inventory(db, device=device, payload=payload.inventory, now=now)
    if payload.remote_access is not None:
        upsert_rustdesk_status(db, device=device, payload=payload.remote_access, now=now)
    db.flush()
    evaluate_device_alerts(db, device=device, checkin_payload=checkin_payload, now=now)
    _audit(
        db,
        organization_id=device.organization_id,
        action="agent.checkin",
        target_type="device",
        target_id=str(device.id),
        metadata={"status": payload.health_status, "agent_version": payload.agent_version},
    )
    db.commit()
    db.refresh(checkin)
    return AgentCheckinResponse(
        status="accepted", device_id=device.id, checked_in_at=checkin.checked_in_at
    )


def _authenticate_agent_jobs(db: Session, payload: AgentJobPollRequest) -> Agent:
    agent = db.scalar(select(Agent).where(Agent.device_id == payload.device_id))
    if agent is None or not verify_token(payload.device_secret, agent.device_secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials"
        )
    return agent


@router.get("/jobs", response_model=list[AgentJobResponse])
def poll_jobs(
    device_id: UUID | None = None,
    device_secret: str | None = None,
    x_cyclope_device_id: UUID | None = Header(default=None),
    x_cyclope_device_secret: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> list[AgentJobResponse]:
    """Assign and return queued safe built-in jobs for the authenticated device.

    The agent sends credentials in headers to avoid exposing secrets in URLs.
    Query parameters remain accepted for local tests and explicit API clients.
    """
    auth_device_id = x_cyclope_device_id or device_id
    auth_device_secret = x_cyclope_device_secret or device_secret
    if auth_device_id is None or auth_device_secret is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials"
        )
    agent = _authenticate_agent_jobs(
        db, AgentJobPollRequest(device_id=auth_device_id, device_secret=auth_device_secret)
    )
    jobs = assign_jobs_for_agent(db, agent)
    db.commit()
    return [job_response(db, job) for job in jobs]


@router.post("/jobs/{job_id}/start", response_model=AgentJobResponse)
def start_polled_job(
    job_id: UUID, payload: AgentJobPollRequest, db: Session = Depends(get_db)
) -> AgentJobResponse:
    agent = _authenticate_agent_jobs(db, payload)
    job = db.get(AgentJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    start_job(db, job, agent)
    db.commit()
    return job_response(db, job, include_events=True)


@router.post("/jobs/{job_id}/complete", response_model=AgentJobResponse)
def complete_polled_job(
    job_id: UUID, payload: AgentJobCompleteRequest, db: Session = Depends(get_db)
) -> AgentJobResponse:
    agent = _authenticate_agent_jobs(db, payload)
    job = db.get(AgentJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    complete_job(
        db,
        job,
        agent,
        succeeded=payload.succeeded,
        output=payload.output,
        error=payload.error,
        exit_code=payload.exit_code,
        metadata=payload.metadata,
    )
    db.commit()
    return job_response(db, job, include_events=True)
