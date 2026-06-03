from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.jobs import ALLOWED_JOB_TYPES
from app.core.security import hash_password, require_permission, verify_password
from app.core.token_hashing import generate_secret, hash_token
from app.db.session import get_db
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.phase2 import AIInsight, Asset, DiscoveredDevice, DocumentationArticle, ReportRun, ReportSchedule, ReportTemplate, Ticket
from app.models.phase3 import APIKey, BackupJob, BackupRun, DashboardPreference, PortalRole, PortalSession, PortalUser, ServiceStatus, SystemHealth, Workflow, WorkflowAction, WorkflowExecution, WorkflowTrigger
from app.models.remote_session_audit import RemoteSessionAudit
from app.models.user import User

router = APIRouter(tags=["phase3"])

TRIGGERS = {"alert_created", "ticket_created", "device_offline", "warranty_expiring", "discovery_complete"}
ACTIONS = {"create_ticket", "send_notification", "run_approved_agent_job", "generate_report"}
REPORT_TYPES = {"executive_summary", "asset_inventory", "device_inventory", "ticket_metrics", "alert_metrics", "security_overview", "warranty_status"}
REPORT_FORMATS = {"pdf", "csv", "json"}


class DashboardPreferenceRequest(BaseModel):
    layout: dict = Field(default_factory=dict)
    role_widgets: list[str] = Field(default_factory=list)


class PortalUserCreateRequest(BaseModel):
    email: str
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=12)
    role_name: str = "customer_user"


class PortalLoginRequest(BaseModel):
    email: str
    password: str


class WorkflowRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    trigger_type: str
    action_type: str
    action_config: dict = Field(default_factory=dict)
    enabled: bool = True


class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=lambda: ["devices:read"])


class BackupJobRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    schedule: str = Field(pattern="^(daily|weekly|monthly)$")
    target: str = Field(min_length=1, max_length=512)
    enabled: bool = True


class ReportRunRequest(BaseModel):
    report_type: str = Field(pattern="^(executive_summary|asset_inventory|device_inventory|ticket_metrics|alert_metrics|security_overview|warranty_status)$")
    format: str = Field(pattern="^(pdf|csv|json)$")


def now_utc() -> datetime:
    return datetime.now(UTC)


def audit(db: Session, user: User, action: str, target_type: str, target_id: str | None, metadata: dict) -> None:
    db.add(AuditLog(organization_id=user.organization_id, actor_user_id=user.id, action=action, target_type=target_type, target_id=target_id, metadata_json=metadata))


@router.get("/dashboard/operations")
def operations_dashboard(current: User = Depends(require_permission("dashboard:read")), db: Session = Depends(get_db)) -> dict:
    org = current.organization_id
    counts = {
        "total_devices": db.scalar(select(func.count()).select_from(Device).where(Device.organization_id == org)) or 0,
        "offline_devices": db.scalar(select(func.count()).select_from(Device).where(Device.organization_id == org, Device.is_online.is_(False))) or 0,
        "active_alerts": db.scalar(select(func.count()).select_from(Alert).where(Alert.organization_id == org, Alert.status == "active")) or 0,
        "open_tickets": db.scalar(select(func.count()).select_from(Ticket).where(Ticket.organization_id == org, Ticket.status.notin_(["Resolved", "Closed"]))) or 0,
        "discovered_devices": db.scalar(select(func.count()).select_from(DiscoveredDevice).where(DiscoveredDevice.organization_id == org)) or 0,
        "assets": db.scalar(select(func.count()).select_from(Asset).where(Asset.organization_id == org)) or 0,
        "warranty_expiring": db.scalar(select(func.count()).select_from(Asset).where(Asset.organization_id == org, Asset.warranty_expiration <= datetime.now(UTC).date() + timedelta(days=30))) or 0,
        "recent_remote_sessions": db.scalar(select(func.count()).select_from(RemoteSessionAudit).where(RemoteSessionAudit.organization_id == org)) or 0,
        "recent_documentation_updates": db.scalar(select(func.count()).select_from(DocumentationArticle).where(DocumentationArticle.organization_id == org)) or 0,
        "ai_insights": db.scalar(select(func.count()).select_from(AIInsight).where(AIInsight.organization_id == org)) or 0,
        "report_runs": db.scalar(select(func.count()).select_from(ReportRun).where(ReportRun.organization_id == org)) or 0,
    }
    role_widgets = {
        "viewer": ["device_health", "active_alerts", "open_tickets", "asset_summary"],
        "technician": ["device_health", "active_alerts", "open_tickets", "discovery_results", "warranty_summary"],
        "admin": ["device_health", "active_alerts", "open_tickets", "asset_summary", "report_status", "platform_health"],
        "owner": ["device_health", "active_alerts", "open_tickets", "asset_summary", "recent_remote_sessions", "ai_insights", "report_status", "platform_health"],
    }
    return {"widgets": counts, "role_widgets": role_widgets.get(current.role, role_widgets["viewer"])}


@router.get("/dashboard/preferences")
def get_dashboard_preferences(current: User = Depends(require_permission("dashboard:read")), db: Session = Depends(get_db)) -> dict:
    pref = db.scalar(select(DashboardPreference).where(DashboardPreference.organization_id == current.organization_id, DashboardPreference.user_id == current.id))
    if pref is None:
        return {"layout": {}, "role_widgets": []}
    return {"layout": pref.layout, "role_widgets": pref.role_widgets}


@router.put("/dashboard/preferences")
def save_dashboard_preferences(payload: DashboardPreferenceRequest, current: User = Depends(require_permission("dashboard:read")), db: Session = Depends(get_db)) -> dict:
    pref = db.scalar(select(DashboardPreference).where(DashboardPreference.organization_id == current.organization_id, DashboardPreference.user_id == current.id))
    if pref is None:
        pref = DashboardPreference(organization_id=current.organization_id, user_id=current.id, layout=payload.layout, role_widgets=payload.role_widgets)
        db.add(pref)
    else:
        pref.layout = payload.layout
        pref.role_widgets = payload.role_widgets
    audit(db, current, "dashboard.preferences.saved", "dashboard_preference", str(pref.id), {})
    db.commit()
    return {"layout": pref.layout, "role_widgets": pref.role_widgets}


@router.post("/portal/users", status_code=status.HTTP_201_CREATED)
def create_portal_user(payload: PortalUserCreateRequest, current: User = Depends(require_permission("portal:manage")), db: Session = Depends(get_db)) -> dict:
    role = db.scalar(select(PortalRole).where(PortalRole.organization_id == current.organization_id, PortalRole.name == payload.role_name))
    if role is None:
        role = PortalRole(organization_id=current.organization_id, name=payload.role_name, permissions=["tickets:create", "tickets:read", "assets:read", "devices:read", "documentation:read", "reports:download"])
        db.add(role)
        db.flush()
    portal_user = PortalUser(organization_id=current.organization_id, portal_role_id=role.id, email=payload.email, display_name=payload.display_name, hashed_password=hash_password(payload.password), is_active=True)
    db.add(portal_user)
    db.flush()
    audit(db, current, "portal.user.created", "portal_user", str(portal_user.id), {})
    db.commit()
    return {"id": portal_user.id, "email": portal_user.email, "display_name": portal_user.display_name, "role": role.name}


@router.post("/portal/login")
def portal_login(payload: PortalLoginRequest, db: Session = Depends(get_db)) -> dict:
    portal_user = db.scalar(select(PortalUser).where(PortalUser.email == payload.email, PortalUser.is_active.is_(True)))
    if portal_user is None or not verify_password(payload.password, portal_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid portal credentials")
    token = generate_secret()
    session = PortalSession(organization_id=portal_user.organization_id, portal_user_id=portal_user.id, token_hash=hash_token(token), expires_at=now_utc() + timedelta(hours=8), created_at=now_utc())
    db.add(session)
    db.commit()
    return {"portal_token": token, "portal_user": {"id": portal_user.id, "email": portal_user.email, "organization_id": portal_user.organization_id}}


@router.post("/automation/workflows", status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowRequest, current: User = Depends(require_permission("automation:manage")), db: Session = Depends(get_db)) -> dict:
    if payload.trigger_type not in TRIGGERS or payload.action_type not in ACTIONS:
        raise HTTPException(status_code=400, detail="Unsupported workflow trigger or action")
    if payload.action_type == "run_approved_agent_job" and payload.action_config.get("job_type") not in ALLOWED_JOB_TYPES:
        raise HTTPException(status_code=400, detail="Workflow job action must use an approved agent job type")
    workflow = Workflow(organization_id=current.organization_id, name=payload.name, enabled=payload.enabled)
    db.add(workflow)
    db.flush()
    db.add(WorkflowTrigger(organization_id=current.organization_id, workflow_id=workflow.id, trigger_type=payload.trigger_type, config={}))
    db.add(WorkflowAction(organization_id=current.organization_id, workflow_id=workflow.id, action_type=payload.action_type, config=payload.action_config))
    audit(db, current, "workflow.created", "workflow", str(workflow.id), {"trigger": payload.trigger_type, "action": payload.action_type})
    db.commit()
    return {"id": workflow.id, "name": workflow.name, "enabled": workflow.enabled}


@router.post("/automation/workflows/{workflow_id}/execute", status_code=status.HTTP_201_CREATED)
def execute_workflow(workflow_id: UUID, current: User = Depends(require_permission("automation:manage")), db: Session = Depends(get_db)) -> dict:
    workflow = db.get(Workflow, workflow_id)
    if workflow is None or workflow.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    execution = WorkflowExecution(organization_id=current.organization_id, workflow_id=workflow.id, status="queued", trigger_payload={"manual": True})
    db.add(execution)
    db.flush()
    audit(db, current, "workflow.execution.created", "workflow", str(workflow.id), {})
    db.commit()
    return {"id": execution.id, "workflow_id": workflow.id, "status": execution.status}


@router.post("/platform/api-keys", status_code=status.HTTP_201_CREATED)
def create_api_key(payload: APIKeyCreateRequest, current: User = Depends(require_permission("api_keys:manage")), db: Session = Depends(get_db)) -> dict:
    raw_key = "cc_" + generate_secret()
    prefix = raw_key[:12]
    api_key = APIKey(organization_id=current.organization_id, name=payload.name, key_hash=hash_token(raw_key), prefix=prefix, scopes=payload.scopes)
    db.add(api_key)
    db.flush()
    audit(db, current, "api_key.created", "api_key", str(api_key.id), {"prefix": prefix, "scopes": payload.scopes})
    db.commit()
    return {"id": api_key.id, "name": api_key.name, "prefix": prefix, "scopes": api_key.scopes, "api_key": raw_key}


@router.get("/platform/api-keys")
def list_api_keys(current: User = Depends(require_permission("api_keys:manage")), db: Session = Depends(get_db)) -> list[dict]:
    keys = db.scalars(select(APIKey).where(APIKey.organization_id == current.organization_id).order_by(APIKey.created_at.desc())).all()
    return [{"id": key.id, "name": key.name, "prefix": key.prefix, "scopes": key.scopes, "revoked_at": key.revoked_at, "last_used_at": key.last_used_at} for key in keys]


@router.get("/platform/health")
def platform_health(current: User = Depends(require_permission("platform:read")), db: Session = Depends(get_db)) -> dict:
    checked = now_utc()
    statuses = []
    try:
        db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:
        database_status = "degraded"
    for name, state, details in [
        ("backend", "ok", {"version": "api"}),
        ("database", database_status, {}),
        ("redis", "configured", {"check": "connection validation is deployment-specific"}),
        ("rustdesk-hbbs", "configured", {"ports": [21115, 21116, 21118]}),
        ("rustdesk-hbbr", "configured", {"ports": [21117, 21119]}),
        ("agent-connectivity", "observed", {"source": "device check-ins"}),
    ]:
        db.add(SystemHealth(organization_id=current.organization_id, component=name, status=state, details=details, checked_at=checked))
        statuses.append({"component": name, "status": state, "details": details, "checked_at": checked})
    db.commit()
    return {"status": database_status if database_status != "ok" else "ok", "services": statuses}


@router.post("/backups/jobs", status_code=status.HTTP_201_CREATED)
def create_backup_job(payload: BackupJobRequest, current: User = Depends(require_permission("backups:manage")), db: Session = Depends(get_db)) -> dict:
    job = BackupJob(organization_id=current.organization_id, name=payload.name, schedule=payload.schedule, enabled=payload.enabled, target=payload.target)
    db.add(job)
    db.flush()
    audit(db, current, "backup.job.created", "backup_job", str(job.id), {"schedule": job.schedule})
    db.commit()
    return {"id": job.id, "name": job.name, "schedule": job.schedule, "enabled": job.enabled}


@router.post("/backups/jobs/{job_id}/runs", status_code=status.HTTP_201_CREATED)
def record_backup_run(job_id: UUID, current: User = Depends(require_permission("backups:manage")), db: Session = Depends(get_db)) -> dict:
    job = db.get(BackupJob, job_id)
    if job is None or job.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Backup job not found")
    run = BackupRun(organization_id=current.organization_id, job_id=job.id, status="recorded", validation_status="pending", notes="Backup run recorded; automated restore is intentionally not implemented.")
    db.add(run)
    db.flush()
    audit(db, current, "backup.run.recorded", "backup_run", str(run.id), {})
    db.commit()
    return {"id": run.id, "status": run.status, "validation_status": run.validation_status}


@router.post("/reports/phase3/runs", status_code=status.HTTP_201_CREATED)
def create_phase3_report_run(payload: ReportRunRequest, current: User = Depends(require_permission("reports:write")), db: Session = Depends(get_db)) -> dict:
    template = ReportTemplate(organization_id=current.organization_id, name=payload.report_type.replace("_", " ").title(), report_type=payload.report_type, config={"phase": 3})
    db.add(template)
    db.flush()
    run = ReportRun(organization_id=current.organization_id, template_id=template.id, status="queued", format=payload.format)
    db.add(run)
    db.flush()
    audit(db, current, "report.phase3.created", "report_run", str(run.id), {"format": payload.format, "report_type": payload.report_type})
    db.commit()
    return {"id": run.id, "template_id": template.id, "status": run.status, "format": run.format, "delivery": ["email", "portal_download"]}
