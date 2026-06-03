from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class RemoteSessionAudit(UUIDPrimaryKeyMixin, Base):
    """Append-only audit trail for RustDesk launch attempts from Cyclope Central."""

    __tablename__ = "remote_session_audits"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), index=True
    )
    provider_config_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("remote_provider_configs.id"), nullable=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    provider_type: Mapped[str] = mapped_column(String(64), nullable=False, default="rustdesk_oss")
    action: Mapped[str] = mapped_column(String(128), nullable=False, default="remote.launch")
    launch_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    device = relationship("Device")
    provider_config = relationship("RemoteProviderConfig", back_populates="session_audits")
    actor = relationship("User")
