"""production readiness phase 3

Revision ID: 0010_production_readiness_phase3
Revises: 0009_msp_operations_phase2
Create Date: 2026-06-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_production_readiness_phase3"
down_revision: str | None = "0009_msp_operations_phase2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def cols() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def org(nullable: bool = False) -> sa.Column:
    return sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=nullable)


def create(name: str, *columns: sa.Column, fks: list[sa.ForeignKeyConstraint] | None = None, org_nullable: bool = False) -> None:
    constraints = [sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]), *(fks or []), sa.PrimaryKeyConstraint("id")]
    op.create_table(name, org(org_nullable), *columns, *cols(), *constraints)
    op.create_index(op.f(f"ix_{name}_organization_id"), name, ["organization_id"], unique=False)


def upgrade() -> None:
    create("dashboard_preferences", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("layout", sa.JSON(), nullable=False), sa.Column("role_widgets", sa.JSON(), nullable=False), fks=[sa.ForeignKeyConstraint(["user_id"], ["users.id"])])
    create("portal_roles", sa.Column("name", sa.String(64), nullable=False), sa.Column("permissions", sa.JSON(), nullable=False))
    create("portal_users", sa.Column("portal_role_id", postgresql.UUID(as_uuid=True)), sa.Column("email", sa.String(320), nullable=False), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("hashed_password", sa.String(255), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), fks=[sa.ForeignKeyConstraint(["portal_role_id"], ["portal_roles.id"])])
    create("portal_sessions", sa.Column("portal_user_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("token_hash", sa.String(255), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("revoked_at", sa.DateTime(timezone=True)), fks=[sa.ForeignKeyConstraint(["portal_user_id"], ["portal_users.id"])])
    create("workflows", sa.Column("name", sa.String(255), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False))
    create("workflow_triggers", sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("trigger_type", sa.String(128), nullable=False), sa.Column("config", sa.JSON(), nullable=False), fks=[sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"])])
    create("workflow_actions", sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("action_type", sa.String(128), nullable=False), sa.Column("config", sa.JSON(), nullable=False), fks=[sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"])])
    create("workflow_executions", sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("trigger_payload", sa.JSON(), nullable=False), sa.Column("completed_at", sa.DateTime(timezone=True)), fks=[sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"])])
    create("api_keys", sa.Column("name", sa.String(255), nullable=False), sa.Column("key_hash", sa.String(255), nullable=False), sa.Column("prefix", sa.String(32), nullable=False), sa.Column("scopes", sa.JSON(), nullable=False), sa.Column("last_used_at", sa.DateTime(timezone=True)), sa.Column("revoked_at", sa.DateTime(timezone=True)))
    create("system_health", sa.Column("component", sa.String(128), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("details", sa.JSON(), nullable=False), sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False), org_nullable=True)
    create("service_statuses", sa.Column("service_name", sa.String(128), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("details", sa.JSON(), nullable=False), sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False), org_nullable=True)
    create("backup_jobs", sa.Column("name", sa.String(255), nullable=False), sa.Column("schedule", sa.String(128), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("target", sa.String(512), nullable=False), org_nullable=True)
    create("backup_runs", sa.Column("job_id", postgresql.UUID(as_uuid=True)), sa.Column("status", sa.String(64), nullable=False), sa.Column("backup_path", sa.String(512)), sa.Column("validation_status", sa.String(64)), sa.Column("notes", sa.Text()), sa.Column("completed_at", sa.DateTime(timezone=True)), fks=[sa.ForeignKeyConstraint(["job_id"], ["backup_jobs.id"])], org_nullable=True)


def downgrade() -> None:
    for table in ["backup_runs", "backup_jobs", "service_statuses", "system_health", "api_keys", "workflow_executions", "workflow_actions", "workflow_triggers", "workflows", "portal_sessions", "portal_users", "portal_roles", "dashboard_preferences"]:
        op.drop_table(table)
