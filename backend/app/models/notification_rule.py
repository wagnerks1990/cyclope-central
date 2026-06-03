from uuid import UUID

from sqlalchemy import JSON, Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class NotificationRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant-scoped alert-to-channel routing rule."""

    __tablename__ = "notification_rules"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    severity_filter: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    alert_rule_type_filter: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    channel_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
