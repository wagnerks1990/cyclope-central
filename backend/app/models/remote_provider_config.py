from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RemoteProviderConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tenant-scoped remote access provider configuration.

    RustDesk OSS is integrated as an external provider only; Cyclope Central does not
    implement custom screen capture, keyboard input, or remote desktop transport.
    """

    __tablename__ = "remote_provider_configs"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False, default="rustdesk_oss")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    relay_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    public_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    device_links = relationship("RemoteDeviceLink", back_populates="provider_config")
    session_audits = relationship("RemoteSessionAudit", back_populates="provider_config")
