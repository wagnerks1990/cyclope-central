"""rustdesk remote access provider

Revision ID: 0008_rustdesk_remote_access
Revises: 0007_auth_rbac
Create Date: 2026-06-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_rustdesk_remote_access"
down_revision: str | None = "0007_auth_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "remote_provider_configs",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("relay_host", sa.String(length=255), nullable=True),
        sa.Column("public_key", sa.String(length=1024), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_remote_provider_configs_organization_id"), "remote_provider_configs", ["organization_id"], unique=False)

    op.create_table(
        "remote_device_links",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("rustdesk_id", sa.String(length=128), nullable=True),
        sa.Column("installed", sa.Boolean(), nullable=False),
        sa.Column("last_status", sa.String(length=64), nullable=False),
        sa.Column("last_reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["provider_config_id"], ["remote_provider_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_remote_device_links_device_id"), "remote_device_links", ["device_id"], unique=False)
    op.create_index(op.f("ix_remote_device_links_organization_id"), "remote_device_links", ["organization_id"], unique=False)
    op.create_index(op.f("ix_remote_device_links_provider_config_id"), "remote_device_links", ["provider_config_id"], unique=False)
    op.create_index(op.f("ix_remote_device_links_rustdesk_id"), "remote_device_links", ["rustdesk_id"], unique=False)

    op.create_table(
        "remote_session_audits",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_config_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_type", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("launch_url", sa.String(length=512), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["provider_config_id"], ["remote_provider_configs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_remote_session_audits_actor_user_id"), "remote_session_audits", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_remote_session_audits_organization_id"), "remote_session_audits", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_table("remote_session_audits")
    op.drop_table("remote_device_links")
    op.drop_table("remote_provider_configs")
