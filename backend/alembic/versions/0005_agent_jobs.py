"""safe agent jobs

Revision ID: 0005_agent_jobs
Revises: 0004_alerts
Create Date: 2026-06-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_agent_jobs"
down_revision: str | None = "0004_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_jobs",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_summary", sa.String(length=512), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assigned_agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_jobs_assigned_agent_id"), "agent_jobs", ["assigned_agent_id"], unique=False)
    op.create_index(op.f("ix_agent_jobs_device_id"), "agent_jobs", ["device_id"], unique=False)
    op.create_index(op.f("ix_agent_jobs_job_type"), "agent_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_agent_jobs_organization_id"), "agent_jobs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_agent_jobs_status"), "agent_jobs", ["status"], unique=False)
    op.create_table(
        "agent_job_results",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["agent_jobs.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_job_results_job_id"), "agent_job_results", ["job_id"], unique=True)
    op.create_index(op.f("ix_agent_job_results_organization_id"), "agent_job_results", ["organization_id"], unique=False)
    op.create_table(
        "agent_job_events",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=1024), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["agent_jobs.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_job_events_event_type"), "agent_job_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_agent_job_events_job_id"), "agent_job_events", ["job_id"], unique=False)
    op.create_index(op.f("ix_agent_job_events_organization_id"), "agent_job_events", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_job_events")
    op.drop_table("agent_job_results")
    op.drop_table("agent_jobs")
