"""endpoint inventory tables

Revision ID: 0003_endpoint_inventory
Revises: 0002_agent_enrollment
Create Date: 2026-06-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003_endpoint_inventory"
down_revision: str | None = "0002_agent_enrollment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_inventories",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=False),
        sa.Column("operating_system", sa.String(length=128), nullable=False),
        sa.Column("os_version", sa.String(length=128), nullable=True),
        sa.Column("os_build", sa.String(length=128), nullable=True),
        sa.Column("architecture", sa.String(length=64), nullable=True),
        sa.Column("agent_version", sa.String(length=64), nullable=True),
        sa.Column("cpu_model", sa.String(length=255), nullable=True),
        sa.Column("cpu_cores", sa.Integer(), nullable=True),
        sa.Column("memory_total_bytes", sa.BigInteger(), nullable=True),
        sa.Column("bios_vendor", sa.String(length=255), nullable=True),
        sa.Column("bios_version", sa.String(length=255), nullable=True),
        sa.Column("system_manufacturer", sa.String(length=255), nullable=True),
        sa.Column("system_model", sa.String(length=255), nullable=True),
        sa.Column("inventory_refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_device_inventories_device_id"), "device_inventories", ["device_id"], unique=True)
    op.create_index(op.f("ix_device_inventories_organization_id"), "device_inventories", ["organization_id"], unique=False)
    op.create_table(
        "disk_inventories",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("filesystem", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("free_bytes", sa.BigInteger(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_disk_inventories_device_id"), "disk_inventories", ["device_id"], unique=False)
    op.create_index(op.f("ix_disk_inventories_organization_id"), "disk_inventories", ["organization_id"], unique=False)
    op.create_table(
        "network_interface_inventories",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("mac_address", sa.String(length=64), nullable=True),
        sa.Column("ip_addresses", sa.JSON(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_network_interface_inventories_device_id"), "network_interface_inventories", ["device_id"], unique=False)
    op.create_index(op.f("ix_network_interface_inventories_organization_id"), "network_interface_inventories", ["organization_id"], unique=False)
    op.create_table(
        "installed_software",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=128), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_installed_software_device_id"), "installed_software", ["device_id"], unique=False)
    op.create_index(op.f("ix_installed_software_name"), "installed_software", ["name"], unique=False)
    op.create_index(op.f("ix_installed_software_organization_id"), "installed_software", ["organization_id"], unique=False)
    op.create_table(
        "security_statuses",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("antivirus_product", sa.String(length=255), nullable=True),
        sa.Column("antivirus_enabled", sa.Boolean(), nullable=True),
        sa.Column("antivirus_up_to_date", sa.Boolean(), nullable=True),
        sa.Column("defender_enabled", sa.Boolean(), nullable=True),
        sa.Column("firewall_enabled", sa.Boolean(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_security_statuses_device_id"), "security_statuses", ["device_id"], unique=True)
    op.create_index(op.f("ix_security_statuses_organization_id"), "security_statuses", ["organization_id"], unique=False)
    op.create_table(
        "update_statuses",
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pending_reboot", sa.Boolean(), nullable=True),
        sa.Column("update_status", sa.String(length=128), nullable=True),
        sa.Column("last_update_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_update_statuses_device_id"), "update_statuses", ["device_id"], unique=True)
    op.create_index(op.f("ix_update_statuses_organization_id"), "update_statuses", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_table("update_statuses")
    op.drop_table("security_statuses")
    op.drop_table("installed_software")
    op.drop_table("network_interface_inventories")
    op.drop_table("disk_inventories")
    op.drop_table("device_inventories")
