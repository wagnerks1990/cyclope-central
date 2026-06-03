from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.security import require_permission
from app.db.session import get_db
from app.models.alert import Alert
from app.models.audit_log import AuditLog
from app.models.device import Device
from app.models.device_inventory import DeviceInventory
from app.models.phase2 import (
    AIConversation,
    AIInsight,
    AIMessage,
    Asset,
    Company,
    DiscoveredDevice,
    DiscoveryScan,
    DocumentationArticle,
    DocumentationCategory,
    ReportRun,
    ReportSchedule,
    ReportTemplate,
    Ticket,
    TicketComment,
    TicketTimeEntry,
)
from app.models.user import User

router = APIRouter(tags=["operations"])

ASSET_STATUSES = {"Active", "Spare", "Repair", "Retired", "Lost", "Disposal"}
TICKET_STATUSES = {"New", "Open", "In Progress", "Waiting", "Resolved", "Closed"}
TICKET_PRIORITIES = {"Low", "Medium", "High", "Critical"}
DISCOVERY_TYPES = {"network_discovery", "arp_scan", "dns_discovery", "snmp_discovery"}
REPORT_TYPES = {
    "executive_summary",
    "device_inventory",
    "asset_inventory",
    "warranty_report",
    "alert_summary",
    "ticket_summary",
    "security_status_report",
}


class AssetRequest(BaseModel):
    asset_tag: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    device_id: UUID | None = None
    serial_number: str | None = Field(default=None, max_length=255)
    manufacturer: str | None = Field(default=None, max_length=255)
    model: str | None = Field(default=None, max_length=255)
    purchase_date: date | None = None
    purchase_cost: Decimal | None = None
    vendor: str | None = Field(default=None, max_length=255)
    warranty_expiration: date | None = None
    assigned_user: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=255)
    location: str | None = Field(default=None, max_length=255)
    status: str = "Active"
    notes: str | None = None


class AssetBulkImportRequest(BaseModel):
    assets: list[AssetRequest] = Field(min_length=1, max_length=500)


class CompanyRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    notes: str | None = None


class ArticleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body_markdown: str = Field(min_length=1)
    company_id: UUID | None = None
    category_name: str | None = Field(default=None, max_length=255)
    tags: list[str] = Field(default_factory=list, max_length=50)


class DiscoveryScanRequest(BaseModel):
    scan_type: str = Field(pattern="^(network_discovery|arp_scan|dns_discovery|snmp_discovery)$")
    device_id: UUID | None = None
    scheduled_for: datetime | None = None


class DiscoveredDeviceRequest(BaseModel):
    ip_address: str = Field(min_length=1, max_length=64)
    hostname: str | None = Field(default=None, max_length=255)
    mac_address: str | None = Field(default=None, max_length=64)
    vendor: str | None = Field(default=None, max_length=255)
    open_ports: list[int] = Field(default_factory=list, max_length=256)
    snmp_data: dict = Field(default_factory=dict)


class TicketRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    device_id: UUID | None = None
    asset_id: UUID | None = None
    company_id: UUID | None = None
    alert_id: UUID | None = None
    assigned_user_id: UUID | None = None
    status: str = "New"
    priority: str = "Medium"


class TicketCommentRequest(BaseModel):
    body: str = Field(min_length=1)
    internal: bool = True


class TicketTimeEntryRequest(BaseModel):
    minutes: int = Field(gt=0, le=1440)
    notes: str | None = None


class AIQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)


class ReportTemplateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    report_type: str
    config: dict = Field(default_factory=dict)


class ReportRunRequest(BaseModel):
    template_id: UUID | None = None
    report_type: str | None = None
    format: str = Field(default="csv", pattern="^(csv|pdf)$")


class ReportScheduleRequest(BaseModel):
    template_id: UUID
    cron: str = Field(min_length=1, max_length=128)
    enabled: bool = True
    email_recipients: list[str] = Field(default_factory=list)


def now_utc() -> datetime:
    return datetime.now(UTC)


def audit(db: Session, user: User, action: str, target_type: str, target_id: str | None, metadata: dict) -> None:
    db.add(AuditLog(organization_id=user.organization_id, actor_user_id=user.id, action=action, target_type=target_type, target_id=target_id, metadata_json=metadata))


def ensure_device(db: Session, user: User, device_id: UUID | None) -> Device | None:
    if device_id is None:
        return None
    device = db.get(Device, device_id)
    if device is None or device.organization_id != user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


def asset_to_dict(asset: Asset) -> dict:
    return {
        "id": asset.id,
        "organization_id": asset.organization_id,
        "device_id": asset.device_id,
        "asset_tag": asset.asset_tag,
        "name": asset.name,
        "serial_number": asset.serial_number,
        "manufacturer": asset.manufacturer,
        "model": asset.model,
        "purchase_date": asset.purchase_date,
        "purchase_cost": str(asset.purchase_cost) if asset.purchase_cost is not None else None,
        "vendor": asset.vendor,
        "warranty_expiration": asset.warranty_expiration,
        "assigned_user": asset.assigned_user,
        "department": asset.department,
        "location": asset.location,
        "status": asset.status,
        "notes": asset.notes,
    }


@router.get("/assets")
def list_assets(current: User = Depends(require_permission("assets:read")), db: Session = Depends(get_db)) -> list[dict]:
    return [asset_to_dict(asset) for asset in db.scalars(select(Asset).where(Asset.organization_id == current.organization_id).order_by(Asset.asset_tag)).all()]


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetRequest, current: User = Depends(require_permission("assets:write")), db: Session = Depends(get_db)) -> dict:
    if payload.status not in ASSET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid asset status")
    device = ensure_device(db, current, payload.device_id)
    inventory = db.scalar(select(DeviceInventory).where(DeviceInventory.device_id == device.id)) if device else None
    asset = Asset(
        organization_id=current.organization_id,
        device_id=payload.device_id,
        asset_tag=payload.asset_tag,
        name=payload.name,
        serial_number=payload.serial_number or (device.machine_identifier if device else None),
        manufacturer=payload.manufacturer or (inventory.system_manufacturer if inventory else None),
        model=payload.model or (inventory.system_model if inventory else None),
        purchase_date=payload.purchase_date,
        purchase_cost=payload.purchase_cost,
        vendor=payload.vendor,
        warranty_expiration=payload.warranty_expiration,
        assigned_user=payload.assigned_user,
        department=payload.department,
        location=payload.location,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(asset)
    db.flush()
    audit(db, current, "asset.created", "asset", str(asset.id), {"asset_tag": asset.asset_tag})
    db.commit()
    return asset_to_dict(asset)


@router.post("/assets/bulk-import", status_code=status.HTTP_201_CREATED)
def bulk_import_assets(payload: AssetBulkImportRequest, current: User = Depends(require_permission("assets:write")), db: Session = Depends(get_db)) -> dict:
    created = []
    for item in payload.assets:
        if item.status not in ASSET_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid asset status")
        asset = Asset(organization_id=current.organization_id, **item.model_dump(exclude={"device_id"}), device_id=item.device_id)
        db.add(asset)
        created.append(asset)
    db.flush()
    audit(db, current, "asset.bulk_imported", "asset", None, {"count": len(created)})
    db.commit()
    return {"created": len(created), "assets": [asset_to_dict(asset) for asset in created]}


@router.get("/assets/warranty-alerts")
def warranty_alerts(current: User = Depends(require_permission("assets:read")), db: Session = Depends(get_db)) -> dict:
    today = date.today()
    soon = today + timedelta(days=30)
    expiring = db.scalars(select(Asset).where(Asset.organization_id == current.organization_id, Asset.warranty_expiration >= today, Asset.warranty_expiration <= soon)).all()
    expired = db.scalars(select(Asset).where(Asset.organization_id == current.organization_id, Asset.warranty_expiration < today)).all()
    return {"expiring_30_days": [asset_to_dict(a) for a in expiring], "expired": [asset_to_dict(a) for a in expired]}


@router.get("/documentation/companies")
def list_companies(current: User = Depends(require_permission("documentation:read")), db: Session = Depends(get_db)) -> list[dict]:
    return [{"id": c.id, "name": c.name, "notes": c.notes} for c in db.scalars(select(Company).where(Company.organization_id == current.organization_id).order_by(Company.name)).all()]


@router.post("/documentation/companies", status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyRequest, current: User = Depends(require_permission("documentation:write")), db: Session = Depends(get_db)) -> dict:
    company = Company(organization_id=current.organization_id, name=payload.name, notes=payload.notes)
    db.add(company); db.flush(); audit(db, current, "company.created", "company", str(company.id), {}) ; db.commit()
    return {"id": company.id, "name": company.name, "notes": company.notes}


@router.get("/documentation/articles")
def search_articles(q: str | None = Query(default=None), current: User = Depends(require_permission("documentation:read")), db: Session = Depends(get_db)) -> list[dict]:
    query = select(DocumentationArticle).where(DocumentationArticle.organization_id == current.organization_id)
    if q:
        like = f"%{q}%"
        query = query.where(or_(DocumentationArticle.title.ilike(like), DocumentationArticle.body_markdown.ilike(like)))
    return [{"id": a.id, "title": a.title, "body_markdown": a.body_markdown, "tags": a.tags, "version": a.version} for a in db.scalars(query.order_by(DocumentationArticle.updated_at.desc())).all()]


@router.post("/documentation/articles", status_code=status.HTTP_201_CREATED)
def create_article(payload: ArticleRequest, current: User = Depends(require_permission("documentation:write")), db: Session = Depends(get_db)) -> dict:
    category_id = None
    if payload.category_name:
        category = db.scalar(select(DocumentationCategory).where(DocumentationCategory.organization_id == current.organization_id, DocumentationCategory.name == payload.category_name))
        if category is None:
            category = DocumentationCategory(organization_id=current.organization_id, name=payload.category_name); db.add(category); db.flush()
        category_id = category.id
    article = DocumentationArticle(organization_id=current.organization_id, company_id=payload.company_id, category_id=category_id, title=payload.title, body_markdown=payload.body_markdown, tags=payload.tags, version=1)
    db.add(article); db.flush(); audit(db, current, "documentation.article.created", "documentation_article", str(article.id), {}) ; db.commit()
    return {"id": article.id, "title": article.title, "version": article.version, "tags": article.tags}


@router.get("/discovery/scans")
def list_scans(current: User = Depends(require_permission("discovery:read")), db: Session = Depends(get_db)) -> list[dict]:
    scans = db.scalars(select(DiscoveryScan).where(DiscoveryScan.organization_id == current.organization_id).order_by(DiscoveryScan.created_at.desc())).all()
    return [{"id": s.id, "scan_type": s.scan_type, "status": s.status, "device_id": s.device_id, "scheduled_for": s.scheduled_for} for s in scans]


@router.post("/discovery/scans", status_code=status.HTTP_201_CREATED)
def create_scan(payload: DiscoveryScanRequest, current: User = Depends(require_permission("discovery:write")), db: Session = Depends(get_db)) -> dict:
    ensure_device(db, current, payload.device_id)
    scan = DiscoveryScan(organization_id=current.organization_id, device_id=payload.device_id, scan_type=payload.scan_type, status="scheduled" if payload.scheduled_for else "manual", scheduled_for=payload.scheduled_for)
    db.add(scan); db.flush(); audit(db, current, "discovery.scan.created", "discovery_scan", str(scan.id), {"scan_type": scan.scan_type}) ; db.commit()
    return {"id": scan.id, "scan_type": scan.scan_type, "status": scan.status}


@router.get("/discovery/devices")
def list_discovered(current: User = Depends(require_permission("discovery:read")), db: Session = Depends(get_db)) -> list[dict]:
    devices = db.scalars(select(DiscoveredDevice).where(DiscoveredDevice.organization_id == current.organization_id).order_by(DiscoveredDevice.last_seen_at.desc())).all()
    return [{"id": d.id, "ip_address": d.ip_address, "hostname": d.hostname, "mac_address": d.mac_address, "vendor": d.vendor, "open_ports": d.open_ports, "last_seen_at": d.last_seen_at} for d in devices]


@router.post("/discovery/devices", status_code=status.HTTP_201_CREATED)
def create_discovered(payload: DiscoveredDeviceRequest, current: User = Depends(require_permission("discovery:write")), db: Session = Depends(get_db)) -> dict:
    found = DiscoveredDevice(organization_id=current.organization_id, ip_address=payload.ip_address, hostname=payload.hostname, mac_address=payload.mac_address, vendor=payload.vendor, open_ports=payload.open_ports, snmp_data=payload.snmp_data, last_seen_at=now_utc())
    db.add(found); db.flush(); audit(db, current, "discovery.device.created", "discovered_device", str(found.id), {"ip_address": found.ip_address}) ; db.commit()
    return {"id": found.id, "ip_address": found.ip_address, "hostname": found.hostname}


@router.get("/tickets")
def list_tickets(current: User = Depends(require_permission("tickets:read")), db: Session = Depends(get_db)) -> list[dict]:
    tickets = db.scalars(select(Ticket).where(Ticket.organization_id == current.organization_id).order_by(Ticket.created_at.desc())).all()
    return [{"id": t.id, "title": t.title, "status": t.status, "priority": t.priority, "assigned_user_id": t.assigned_user_id} for t in tickets]


@router.post("/tickets", status_code=status.HTTP_201_CREATED)
def create_ticket(payload: TicketRequest, current: User = Depends(require_permission("tickets:write")), db: Session = Depends(get_db)) -> dict:
    if payload.status not in TICKET_STATUSES or payload.priority not in TICKET_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid ticket status or priority")
    ensure_device(db, current, payload.device_id)
    ticket = Ticket(organization_id=current.organization_id, **payload.model_dump())
    db.add(ticket); db.flush(); audit(db, current, "ticket.created", "ticket", str(ticket.id), {"priority": ticket.priority}) ; db.commit()
    return {"id": ticket.id, "title": ticket.title, "status": ticket.status, "priority": ticket.priority}


@router.post("/tickets/{ticket_id}/comments", status_code=status.HTTP_201_CREATED)
def add_ticket_comment(ticket_id: UUID, payload: TicketCommentRequest, current: User = Depends(require_permission("tickets:write")), db: Session = Depends(get_db)) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or ticket.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    comment = TicketComment(organization_id=current.organization_id, ticket_id=ticket.id, author_user_id=current.id, body=payload.body, internal=payload.internal)
    db.add(comment); db.flush(); audit(db, current, "ticket.comment.created", "ticket", str(ticket.id), {"internal": payload.internal}) ; db.commit()
    return {"id": comment.id, "ticket_id": ticket.id, "internal": comment.internal}


@router.post("/tickets/{ticket_id}/time", status_code=status.HTTP_201_CREATED)
def add_ticket_time(ticket_id: UUID, payload: TicketTimeEntryRequest, current: User = Depends(require_permission("tickets:write")), db: Session = Depends(get_db)) -> dict:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None or ticket.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    entry = TicketTimeEntry(organization_id=current.organization_id, ticket_id=ticket.id, user_id=current.id, minutes=payload.minutes, notes=payload.notes)
    db.add(entry); db.flush(); audit(db, current, "ticket.time.created", "ticket", str(ticket.id), {"minutes": payload.minutes}) ; db.commit()
    return {"id": entry.id, "ticket_id": ticket.id, "minutes": entry.minutes}


@router.post("/ai/query")
def ai_query(payload: AIQueryRequest, current: User = Depends(require_permission("ai:read")), db: Session = Depends(get_db)) -> dict:
    query = payload.query.lower()
    if "offline" in query:
        count = db.scalar(select(func.count()).select_from(Device).where(Device.organization_id == current.organization_id, Device.is_online.is_(False)))
        answer = f"{count} devices are currently offline."
    elif "critical alert" in query:
        count = db.scalar(select(func.count()).select_from(Alert).where(Alert.organization_id == current.organization_id, Alert.severity == "critical", Alert.status == "active"))
        answer = f"{count} active critical alerts need attention."
    elif "warrant" in query:
        soon = date.today() + timedelta(days=30)
        count = db.scalar(select(func.count()).select_from(Asset).where(Asset.organization_id == current.organization_id, Asset.warranty_expiration <= soon))
        answer = f"{count} assets have expired or expiring warranties within 30 days."
    elif "ticket" in query and "assigned" in query:
        count = db.scalar(select(func.count()).select_from(Ticket).where(Ticket.organization_id == current.organization_id, Ticket.assigned_user_id == current.id))
        answer = f"{count} tickets are assigned to you."
    else:
        answer = "I can summarize devices, alerts, warranties, and assigned tickets from tenant-scoped platform data. External LLM providers are not enabled yet."
    conversation = AIConversation(organization_id=current.organization_id, user_id=current.id, title=payload.query[:255])
    db.add(conversation); db.flush()
    db.add(AIMessage(organization_id=current.organization_id, conversation_id=conversation.id, role="user", content=payload.query))
    db.add(AIMessage(organization_id=current.organization_id, conversation_id=conversation.id, role="assistant", content=answer))
    db.add(AIInsight(organization_id=current.organization_id, insight_type="natural_language_query", summary=answer, metadata_json={"provider": "local_stub"}))
    audit(db, current, "ai.query", "ai_conversation", str(conversation.id), {"provider": "local_stub"})
    db.commit()
    return {"answer": answer, "provider": "local_stub", "conversation_id": conversation.id}


@router.get("/reports/templates")
def list_report_templates(current: User = Depends(require_permission("reports:read")), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(ReportTemplate).where(ReportTemplate.organization_id == current.organization_id).order_by(ReportTemplate.name)).all()
    return [{"id": r.id, "name": r.name, "report_type": r.report_type, "config": r.config} for r in rows]


@router.post("/reports/templates", status_code=status.HTTP_201_CREATED)
def create_report_template(payload: ReportTemplateRequest, current: User = Depends(require_permission("reports:write")), db: Session = Depends(get_db)) -> dict:
    if payload.report_type not in REPORT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported report type")
    template = ReportTemplate(organization_id=current.organization_id, name=payload.name, report_type=payload.report_type, config=payload.config)
    db.add(template); db.flush(); audit(db, current, "report.template.created", "report_template", str(template.id), {"report_type": template.report_type}) ; db.commit()
    return {"id": template.id, "name": template.name, "report_type": template.report_type}


@router.post("/reports/runs", status_code=status.HTTP_201_CREATED)
def create_report_run(payload: ReportRunRequest, current: User = Depends(require_permission("reports:write")), db: Session = Depends(get_db)) -> dict:
    if payload.report_type and payload.report_type not in REPORT_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported report type")
    run = ReportRun(organization_id=current.organization_id, template_id=payload.template_id, status="queued", format=payload.format)
    db.add(run); db.flush(); audit(db, current, "report.run.created", "report_run", str(run.id), {"format": run.format}) ; db.commit()
    return {"id": run.id, "status": run.status, "format": run.format}


@router.post("/reports/schedules", status_code=status.HTTP_201_CREATED)
def create_report_schedule(payload: ReportScheduleRequest, current: User = Depends(require_permission("reports:write")), db: Session = Depends(get_db)) -> dict:
    template = db.get(ReportTemplate, payload.template_id)
    if template is None or template.organization_id != current.organization_id:
        raise HTTPException(status_code=404, detail="Report template not found")
    schedule = ReportSchedule(organization_id=current.organization_id, template_id=template.id, cron=payload.cron, enabled=payload.enabled, email_recipients=payload.email_recipients)
    db.add(schedule); db.flush(); audit(db, current, "report.schedule.created", "report_schedule", str(schedule.id), {}) ; db.commit()
    return {"id": schedule.id, "template_id": template.id, "enabled": schedule.enabled}
