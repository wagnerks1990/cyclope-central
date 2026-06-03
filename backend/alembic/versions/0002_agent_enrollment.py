"""agent enrollment and authenticated check-ins

Revision ID: 0002_agent_enrollment
Revises: 0001_initial_foundation
Create Date: 2026-06-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_agent_enrollment"
down_revision: str | None = "0001_initial_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrollment_tokens",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False),
        sa.Column("uses", sa.Integer(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_enrollment_tokens_organization_id"), "enrollment_tokens", ["organization_id"], unique=False)
    op.create_index(op.f("ix_enrollment_tokens_token_hash"), "enrollment_tokens", ["token_hash"], unique=True)
    op.add_column("agents", sa.Column("device_secret_hash", sa.String(length=128), nullable=False, server_default="migrated"))
    op.alter_column("agents", "device_secret_hash", server_default=None)
    op.add_column("devices", sa.Column("architecture", sa.String(length=64), nullable=True))
    op.add_column("devices", sa.Column("machine_identifier", sa.String(length=255), nullable=False, server_default="unknown"))
    op.add_column("devices", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("devices", sa.Column("agent_version", sa.String(length=64), nullable=True))
    op.add_column("devices", sa.Column("health_status", sa.String(length=64), nullable=False, server_default="unknown"))
    op.add_column("devices", sa.Column("is_online", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("devices", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
    op.alter_column("devices", "machine_identifier", server_default=None)
    op.alter_column("devices", "health_status", server_default=None)
    op.alter_column("devices", "is_online", server_default=None)
    op.create_index(op.f("ix_devices_machine_identifier"), "devices", ["machine_identifier"], unique=False)
    op.add_column("device_checkins", sa.Column("ip_address", sa.String(length=64), nullable=True))
    op.add_column("device_checkins", sa.Column("agent_version", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("device_checkins", "agent_version")
    op.drop_column("device_checkins", "ip_address")
    op.drop_index(op.f("ix_devices_machine_identifier"), table_name="devices")
    op.drop_column("devices", "last_seen_at")
    op.drop_column("devices", "is_online")
    op.drop_column("devices", "health_status")
    op.drop_column("devices", "agent_version")
    op.drop_column("devices", "ip_address")
    op.drop_column("devices", "machine_identifier")
    op.drop_column("devices", "architecture")
    op.drop_column("agents", "device_secret_hash")
    op.drop_index(op.f("ix_enrollment_tokens_token_hash"), table_name="enrollment_tokens")
    op.drop_index(op.f("ix_enrollment_tokens_organization_id"), table_name="enrollment_tokens")
    op.drop_table("enrollment_tokens")
