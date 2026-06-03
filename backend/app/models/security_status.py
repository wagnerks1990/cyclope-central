from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SecurityStatus(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Latest endpoint security posture reported by read-only agent inventory."""

    __tablename__ = "security_statuses"

    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), unique=True, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    antivirus_product: Mapped[str | None] = mapped_column(String(255), nullable=True)
    antivirus_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    antivirus_up_to_date: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    defender_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    firewall_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    device = relationship("Device")
