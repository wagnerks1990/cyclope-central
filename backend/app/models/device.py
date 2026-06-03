from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Device(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Managed endpoint inventory record; no remote execution capability is modeled here."""

    __tablename__ = "devices"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    operating_system: Mapped[str] = mapped_column(String(128), nullable=False)
    architecture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    machine_identifier: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    health_status: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="offline")
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="devices")
    agents = relationship("Agent", back_populates="device")
    checkins = relationship("DeviceCheckin", back_populates="device", cascade="all, delete-orphan")
