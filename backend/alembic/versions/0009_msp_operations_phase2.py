"""msp operations phase 2

Revision ID: 0009_msp_operations_phase2
Revises: 0008_rustdesk_remote_access
Create Date: 2026-06-03 00:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_msp_operations_phase2"
down_revision: str | None = "0008_rustdesk_remote_access"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def pk_timestamps() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def org_fk() -> sa.Column:
    return sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False)


def create(name: str, *cols: sa.Column, fks: list[sa.ForeignKeyConstraint] | None = None, indexes: list[str] | None = None) -> None:
    constraints = [sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]), *(fks or []), sa.PrimaryKeyConstraint("id")]
    op.create_table(name, *cols, *pk_timestamps(), *constraints)
    op.create_index(op.f(f"ix_{name}_organization_id"), name, ["organization_id"], unique=False)
    for index in indexes or []:
        op.create_index(op.f(f"ix_{name}_{index}"), name, [index], unique=False)


def upgrade() -> None:
    create("asset_types", org_fk(), sa.Column("name", sa.String(128), nullable=False))
    create("asset_statuses", org_fk(), sa.Column("name", sa.String(64), nullable=False))
    create(
        "assets",
        org_fk(),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("asset_tag", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("serial_number", sa.String(255), nullable=True),
        sa.Column("manufacturer", sa.String(255), nullable=True),
        sa.Column("model", sa.String(255), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=True),
        sa.Column("purchase_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("vendor", sa.String(255), nullable=True),
        sa.Column("warranty_expiration", sa.Date(), nullable=True),
        sa.Column("assigned_user", sa.String(255), nullable=True),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        fks=[sa.ForeignKeyConstraint(["device_id"], ["devices.id"]), sa.ForeignKeyConstraint(["asset_type_id"], ["asset_types.id"])],
        indexes=["device_id", "asset_tag", "serial_number", "warranty_expiration"],
    )
    create("asset_assignments", org_fk(), sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("assigned_user", sa.String(255)), sa.Column("department", sa.String(255)), sa.Column("location", sa.String(255)), sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False), sa.Column("released_at", sa.DateTime(timezone=True)), fks=[sa.ForeignKeyConstraint(["asset_id"], ["assets.id"])], indexes=["asset_id"])
    create("asset_warranties", org_fk(), sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("vendor", sa.String(255)), sa.Column("expires_at", sa.Date(), nullable=False), sa.Column("notes", sa.Text()), fks=[sa.ForeignKeyConstraint(["asset_id"], ["assets.id"])], indexes=["asset_id", "expires_at"])
    create("companies", org_fk(), sa.Column("name", sa.String(255), nullable=False), sa.Column("notes", sa.Text()), indexes=["name"])
    create("contacts", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("name", sa.String(255), nullable=False), sa.Column("email", sa.String(320)), sa.Column("phone", sa.String(64)), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"])])
    create("locations", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("name", sa.String(255), nullable=False), sa.Column("address", sa.Text()), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"])])
    create("documentation_categories", org_fk(), sa.Column("name", sa.String(255), nullable=False))
    create("documentation_articles", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("category_id", postgresql.UUID(as_uuid=True)), sa.Column("title", sa.String(255), nullable=False), sa.Column("body_markdown", sa.Text(), nullable=False), sa.Column("tags", sa.JSON(), nullable=False), sa.Column("version", sa.Integer(), nullable=False), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"]), sa.ForeignKeyConstraint(["category_id"], ["documentation_categories.id"])], indexes=["title"])
    create("network_diagrams", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("title", sa.String(255), nullable=False), sa.Column("diagram_markdown", sa.Text(), nullable=False), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"])])
    create("domain_records", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("domain", sa.String(255), nullable=False), sa.Column("registrar", sa.String(255)), sa.Column("expires_at", sa.Date()), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"])], indexes=["domain"])
    create("ssl_certificates", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("common_name", sa.String(255), nullable=False), sa.Column("issuer", sa.String(255)), sa.Column("expires_at", sa.Date()), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"])])
    create("procedures", org_fk(), sa.Column("title", sa.String(255), nullable=False), sa.Column("body_markdown", sa.Text(), nullable=False))
    create("notes", org_fk(), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("title", sa.String(255), nullable=False), sa.Column("body_markdown", sa.Text(), nullable=False), fks=[sa.ForeignKeyConstraint(["company_id"], ["companies.id"])])
    create("discovery_scans", org_fk(), sa.Column("device_id", postgresql.UUID(as_uuid=True)), sa.Column("scan_type", sa.String(64), nullable=False), sa.Column("status", sa.String(64), nullable=False), sa.Column("scheduled_for", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), fks=[sa.ForeignKeyConstraint(["device_id"], ["devices.id"])])
    create("discovered_devices", org_fk(), sa.Column("asset_id", postgresql.UUID(as_uuid=True)), sa.Column("ip_address", sa.String(64), nullable=False), sa.Column("hostname", sa.String(255)), sa.Column("mac_address", sa.String(64)), sa.Column("vendor", sa.String(255)), sa.Column("open_ports", sa.JSON(), nullable=False), sa.Column("snmp_data", sa.JSON(), nullable=False), sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False), fks=[sa.ForeignKeyConstraint(["asset_id"], ["assets.id"])], indexes=["ip_address"])
    create("discovery_results", org_fk(), sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("discovered_device_id", postgresql.UUID(as_uuid=True)), sa.Column("result", sa.JSON(), nullable=False), fks=[sa.ForeignKeyConstraint(["scan_id"], ["discovery_scans.id"]), sa.ForeignKeyConstraint(["discovered_device_id"], ["discovered_devices.id"])], indexes=["scan_id"])
    create("tickets", org_fk(), sa.Column("device_id", postgresql.UUID(as_uuid=True)), sa.Column("asset_id", postgresql.UUID(as_uuid=True)), sa.Column("company_id", postgresql.UUID(as_uuid=True)), sa.Column("alert_id", postgresql.UUID(as_uuid=True)), sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True)), sa.Column("title", sa.String(255), nullable=False), sa.Column("description", sa.Text()), sa.Column("status", sa.String(64), nullable=False), sa.Column("priority", sa.String(64), nullable=False), fks=[sa.ForeignKeyConstraint(["device_id"], ["devices.id"]), sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]), sa.ForeignKeyConstraint(["company_id"], ["companies.id"]), sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]), sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"])], indexes=["title"])
    create("ticket_statuses", org_fk(), sa.Column("name", sa.String(64), nullable=False))
    create("ticket_priorities", org_fk(), sa.Column("name", sa.String(64), nullable=False))
    create("ticket_comments", org_fk(), sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("author_user_id", postgresql.UUID(as_uuid=True)), sa.Column("body", sa.Text(), nullable=False), sa.Column("internal", sa.Boolean(), nullable=False), fks=[sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]), sa.ForeignKeyConstraint(["author_user_id"], ["users.id"])], indexes=["ticket_id"])
    create("ticket_time_entries", org_fk(), sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("user_id", postgresql.UUID(as_uuid=True)), sa.Column("minutes", sa.Integer(), nullable=False), sa.Column("notes", sa.Text()), fks=[sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]), sa.ForeignKeyConstraint(["user_id"], ["users.id"])], indexes=["ticket_id"])
    create("ticket_attachments", org_fk(), sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("filename", sa.String(255), nullable=False), sa.Column("content_type", sa.String(128)), sa.Column("storage_path", sa.String(512), nullable=False), fks=[sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"]),], indexes=["ticket_id"])
    create("ai_conversations", org_fk(), sa.Column("user_id", postgresql.UUID(as_uuid=True)), sa.Column("title", sa.String(255), nullable=False), fks=[sa.ForeignKeyConstraint(["user_id"], ["users.id"])])
    create("ai_messages", org_fk(), sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("role", sa.String(32), nullable=False), sa.Column("content", sa.Text(), nullable=False), fks=[sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"])], indexes=["conversation_id"])
    create("ai_insights", org_fk(), sa.Column("insight_type", sa.String(128), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False))
    create("report_templates", org_fk(), sa.Column("name", sa.String(255), nullable=False), sa.Column("report_type", sa.String(128), nullable=False), sa.Column("config", sa.JSON(), nullable=False))
    create("report_runs", org_fk(), sa.Column("template_id", postgresql.UUID(as_uuid=True)), sa.Column("status", sa.String(64), nullable=False), sa.Column("format", sa.String(16), nullable=False), sa.Column("output_path", sa.String(512)), sa.Column("completed_at", sa.DateTime(timezone=True)), fks=[sa.ForeignKeyConstraint(["template_id"], ["report_templates.id"])])
    create("report_schedules", org_fk(), sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("cron", sa.String(128), nullable=False), sa.Column("enabled", sa.Boolean(), nullable=False), sa.Column("email_recipients", sa.JSON(), nullable=False), fks=[sa.ForeignKeyConstraint(["template_id"], ["report_templates.id"])], indexes=["template_id"])


def downgrade() -> None:
    for table in [
        "report_schedules", "report_runs", "report_templates", "ai_insights", "ai_messages", "ai_conversations",
        "ticket_attachments", "ticket_time_entries", "ticket_comments", "ticket_priorities", "ticket_statuses", "tickets",
        "discovery_results", "discovered_devices", "discovery_scans", "notes", "procedures", "ssl_certificates",
        "domain_records", "network_diagrams", "documentation_articles", "documentation_categories", "locations", "contacts",
        "companies", "asset_warranties", "asset_assignments", "assets", "asset_statuses", "asset_types",
    ]:
        op.drop_table(table)
