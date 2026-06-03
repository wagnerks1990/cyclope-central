from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AssetType(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_types"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class AssetStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_statuses"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    device_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("devices.id"), nullable=True, index=True)
    asset_type_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("asset_types.id"), nullable=True)
    asset_tag: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    warranty_expiration: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    assigned_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="Active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    device = relationship("Device")


class AssetAssignment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_assignments"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    asset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assets.id"), index=True)
    assigned_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AssetWarranty(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_warranties"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    asset_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("assets.id"), index=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class Contact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contacts"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Location(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)


class DocumentationCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documentation_categories"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class DocumentationArticle(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documentation_articles"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    category_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("documentation_categories.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class NetworkDiagram(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "network_diagrams"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    diagram_markdown: Mapped[str] = mapped_column(Text, nullable=False)


class DomainRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "domain_records"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    registrar: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class SSLCertificate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ssl_certificates"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    common_name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)


class Procedure(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "procedures"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)


class Note(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notes"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)


class DiscoveryScan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovery_scans"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    device_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    scan_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="scheduled")
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DiscoveredDevice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovered_devices"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    asset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    open_ports: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    snmp_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DiscoveryResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "discovery_results"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    scan_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("discovery_scans.id"), index=True)
    discovered_device_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("discovered_devices.id"), nullable=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class Ticket(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tickets"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    device_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("devices.id"), nullable=True)
    asset_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("assets.id"), nullable=True)
    company_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    alert_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("alerts.id"), nullable=True)
    assigned_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="New")
    priority: Mapped[str] = mapped_column(String(64), nullable=False, default="Medium")


class TicketStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticket_statuses"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class TicketPriority(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticket_priorities"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)


class TicketComment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticket_comments"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), index=True)
    author_user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TicketTimeEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticket_time_entries"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class TicketAttachment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ticket_attachments"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    ticket_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tickets.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)


class AIConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_conversations"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)


class AIMessage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_messages"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    conversation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("ai_conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class AIInsight(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ai_insights"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    insight_type: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ReportTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_templates"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class ReportRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_runs"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    template_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("report_templates.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    format: Mapped[str] = mapped_column(String(16), nullable=False, default="csv")
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReportSchedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "report_schedules"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    template_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("report_templates.id"), index=True)
    cron: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    email_recipients: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
