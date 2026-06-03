from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.schemas import (
    AgentJobCreateRequest,
    AgentJobEventResponse,
    AgentJobResponse,
    AgentJobResultResponse,
)
from app.core.jobs import cancel_job, create_job, expire_jobs
from app.core.security import require_permission
from app.db.session import get_db
from app.models.agent_job import AgentJob
from app.models.agent_job_event import AgentJobEvent
from app.models.agent_job_result import AgentJobResult
from app.models.device import Device
from app.models.user import User

router = APIRouter(tags=["jobs"])


def job_response(db: Session, job: AgentJob, include_events: bool = False) -> AgentJobResponse:
    result = db.scalar(select(AgentJobResult).where(AgentJobResult.job_id == job.id))
    events = []
    if include_events:
        events = [
            AgentJobEventResponse(
                id=event.id,
                event_type=event.event_type,
                message=event.message,
                metadata_json=event.metadata_json,
                created_at=event.created_at,
            )
            for event in db.scalars(
                select(AgentJobEvent)
                .where(AgentJobEvent.job_id == job.id)
                .order_by(AgentJobEvent.created_at)
            )
        ]
    return AgentJobResponse(
        id=job.id,
        organization_id=job.organization_id,
        device_id=job.device_id,
        assigned_agent_id=job.assigned_agent_id,
        job_type=job.job_type,
        status=job.status,
        payload=job.payload,
        expires_at=job.expires_at,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        result_summary=job.result_summary,
        result=(
            AgentJobResultResponse(
                id=result.id,
                status=result.status,
                output=result.output,
                error=result.error,
                exit_code=result.exit_code,
                metadata_json=result.metadata_json,
                created_at=result.created_at,
            )
            if result
            else None
        ),
        events=events,
    )


@router.post(
    "/devices/{device_id}/jobs",
    response_model=AgentJobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_device_job(
    device_id: UUID,
    payload: AgentJobCreateRequest,
    current: User = Depends(require_permission("jobs:create")),
    db: Session = Depends(get_db),
) -> AgentJobResponse:
    device = db.get(Device, device_id)
    if device is None or device.organization_id != current.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    job = create_job(db, device=device, job_type=payload.job_type, payload=payload.payload)
    db.commit()
    return job_response(db, job, include_events=True)


@router.get("/devices/{device_id}/jobs", response_model=list[AgentJobResponse])
def list_device_jobs(
    device_id: UUID,
    current: User = Depends(require_permission("jobs:read")),
    db: Session = Depends(get_db),
) -> list[AgentJobResponse]:
    device = db.get(Device, device_id)
    if device is None or device.organization_id != current.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    expire_jobs(db, device_id=device_id)
    db.commit()
    jobs = db.scalars(
        select(AgentJob)
        .where(AgentJob.device_id == device_id, AgentJob.organization_id == current.organization_id)
        .order_by(desc(AgentJob.created_at))
    ).all()
    return [job_response(db, job) for job in jobs]


@router.get("/jobs/{job_id}", response_model=AgentJobResponse)
def get_job(
    job_id: UUID,
    current: User = Depends(require_permission("jobs:read")),
    db: Session = Depends(get_db),
) -> AgentJobResponse:
    job = db.get(AgentJob, job_id)
    if job is None or job.organization_id != current.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    expire_jobs(db, device_id=job.device_id)
    db.commit()
    return job_response(db, job, include_events=True)


@router.post("/jobs/{job_id}/cancel", response_model=AgentJobResponse)
def cancel_agent_job(
    job_id: UUID,
    current: User = Depends(require_permission("jobs:cancel")),
    db: Session = Depends(get_db),
) -> AgentJobResponse:
    job = db.get(AgentJob, job_id)
    if job is None or job.organization_id != current.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    cancel_job(db, job)
    db.commit()
    return job_response(db, job, include_events=True)
