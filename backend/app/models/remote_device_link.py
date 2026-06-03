from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RemoteDeviceLink(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Latest reported mapping between a Cyclope device and an external provider ID."""

    __tablename__ = "remote_device_links"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), index=True
    )
    provider_config_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("remote_provider_configs.id"), nullable=True, index=True
    )
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False, default="rustdesk_oss")
    rustdesk_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    installed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    last_reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device = relationship("Device")
    provider_config = relationship("RemoteProviderConfig", back_populates="device_links")
