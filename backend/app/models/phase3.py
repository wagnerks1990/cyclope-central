from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DashboardPreference(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "dashboard_preferences"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), index=True)
    layout: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    role_widgets: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class PortalRole(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "portal_roles"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    permissions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class PortalUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "portal_users"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    portal_role_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("portal_roles.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PortalSession(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "portal_sessions"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    portal_user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("portal_users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Workflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflows"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkflowTrigger(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_triggers"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    workflow_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workflows.id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class WorkflowAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_actions"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    workflow_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workflows.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class WorkflowExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workflow_executions"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    workflow_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workflows.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="queued")
    trigger_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class APIKey(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "api_keys"
    organization_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    prefix: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SystemHealth(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "system_health"
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    component: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ServiceStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_statuses"
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    service_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BackupJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_jobs"
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    schedule: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    target: Mapped[str] = mapped_column(String(512), nullable=False)


class BackupRun(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "backup_runs"
    organization_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=True, index=True)
    job_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("backup_jobs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    backup_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
