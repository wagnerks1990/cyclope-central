from datetime import UTC, datetime, timedelta
from re import fullmatch
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.agent import Agent
from app.models.agent_job import AgentJob
from app.models.agent_job_event import AgentJobEvent
from app.models.agent_job_result import AgentJobResult
from app.models.audit_log import AuditLog
from app.models.device import Device

ALLOWED_JOB_TYPES = {"ping", "refresh_inventory", "collect_agent_logs", "get_service_status", "network_discovery", "arp_scan", "dns_discovery", "snmp_discovery"}
TERMINAL_JOB_STATUSES = {"succeeded", "failed", "canceled", "expired"}


def now_utc() -> datetime:
    return datetime.now(UTC)


def validate_job_payload(job_type: str, payload: dict | None) -> dict:
    payload = payload or {}
    if job_type not in ALLOWED_JOB_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported job type")
    if job_type in {"ping", "refresh_inventory"}:
        if payload:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Payload not allowed"
            )
        return {}
    if job_type in {"network_discovery", "arp_scan", "dns_discovery", "snmp_discovery"}:
        subnet = str(payload.get("subnet", "local"))
        if not fullmatch(r"[A-Za-z0-9_./:-]{1,128}", subnet):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subnet")
        return {"subnet": subnet}
    if job_type == "collect_agent_logs":
        try:
            line_count = int(payload.get("line_count", 100))
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid line_count"
            ) from exc
        if line_count < 1 or line_count > 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid line_count"
            )
        return {"line_count": line_count}
    service_name = str(payload.get("service_name", ""))
    if not fullmatch(r"[A-Za-z0-9_. -]{1,128}", service_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid service_name")
    return {"service_name": service_name}


def create_job(db: Session, *, device: Device, job_type: str, payload: dict | None) -> AgentJob:
    job = AgentJob(
        organization_id=device.organization_id,
        device_id=device.id,
        job_type=job_type,
        status="queued",
        payload=validate_job_payload(job_type, payload),
        expires_at=now_utc() + timedelta(minutes=settings.agent_job_timeout_minutes),
    )
    db.add(job)
    db.flush()
    add_job_event(db, job, "created", f"Queued safe job {job_type}.", {})
    audit(
        db, device.organization_id, "job.created", "agent_job", str(job.id), {"job_type": job_type}
    )
    return job


def expire_jobs(db: Session, *, device_id: UUID | None = None) -> None:
    query = select(AgentJob).where(
        AgentJob.status.in_(["queued", "assigned", "running"]), AgentJob.expires_at <= now_utc()
    )
    if device_id is not None:
        query = query.where(AgentJob.device_id == device_id)
    for job in db.scalars(query).all():
        job.status = "expired"
        job.completed_at = now_utc()
        add_job_event(db, job, "expired", "Job expired before completion.", {})
        audit(db, job.organization_id, "job.expired", "agent_job", str(job.id), {})


def assign_jobs_for_agent(db: Session, agent: Agent) -> list[AgentJob]:
    expire_jobs(db, device_id=agent.device_id)
    jobs = db.scalars(
        select(AgentJob)
        .where(AgentJob.device_id == agent.device_id, AgentJob.status == "queued")
        .order_by(AgentJob.created_at)
        .limit(5)
    ).all()
    for job in jobs:
        job.status = "assigned"
        job.assigned_agent_id = agent.id
        add_job_event(db, job, "assigned", "Job assigned to polling agent.", {})
        audit(db, job.organization_id, "job.assigned", "agent_job", str(job.id), {})
    db.flush()
    return jobs


def start_job(db: Session, job: AgentJob, agent: Agent) -> AgentJob:
    require_agent_job(job, agent)
    if job.status not in {"assigned", "queued"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job cannot be started")
    job.status = "running"
    job.assigned_agent_id = agent.id
    job.started_at = now_utc()
    add_job_event(db, job, "started", "Agent started job.", {})
    audit(db, job.organization_id, "job.started", "agent_job", str(job.id), {})
    return job


def complete_job(
    db: Session,
    job: AgentJob,
    agent: Agent,
    *,
    succeeded: bool,
    output: str,
    error: str | None,
    exit_code: int | None,
    metadata: dict,
) -> AgentJob:
    require_agent_job(job, agent)
    if job.status != "running":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Job is not running")
    job.status = "succeeded" if succeeded else "failed"
    job.completed_at = now_utc()
    job.result_summary = (output or error or job.status)[:512]
    db.add(
        AgentJobResult(
            organization_id=job.organization_id,
            job_id=job.id,
            status=job.status,
            output=output[:20000],
            error=error[:20000] if error else None,
            exit_code=exit_code,
            metadata_json=metadata,
        )
    )
    event_type = "completed" if succeeded else "failed"
    add_job_event(db, job, event_type, f"Job {job.status}.", {"exit_code": exit_code})
    audit(db, job.organization_id, f"job.{event_type}", "agent_job", str(job.id), {})
    return job


def cancel_job(db: Session, job: AgentJob) -> AgentJob:
    if job.status in TERMINAL_JOB_STATUSES:
        return job
    job.status = "canceled"
    job.completed_at = now_utc()
    add_job_event(db, job, "canceled", "Job canceled by operator.", {})
    audit(db, job.organization_id, "job.canceled", "agent_job", str(job.id), {})
    return job


def require_agent_job(job: AgentJob, agent: Agent) -> None:
    if job.device_id != agent.device_id or (
        job.assigned_agent_id is not None and job.assigned_agent_id != agent.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Job not assigned to agent"
        )


def add_job_event(
    db: Session, job: AgentJob, event_type: str, message: str, metadata: dict
) -> None:
    db.add(
        AgentJobEvent(
            organization_id=job.organization_id,
            job_id=job.id,
            event_type=event_type,
            message=message,
            metadata_json=metadata,
        )
    )


def audit(
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
