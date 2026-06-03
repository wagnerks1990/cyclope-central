from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import UUIDPrimaryKeyMixin


class DeviceCheckin(UUIDPrimaryKeyMixin, Base):
    """Immutable authenticated agent check-in telemetry envelope."""

    __tablename__ = "device_checkins"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), index=True
    )
    agent_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("agents.id"), index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="healthy")
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    checked_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    device = relationship("Device", back_populates="checkins")
    agent = relationship("Agent", back_populates="checkins")
