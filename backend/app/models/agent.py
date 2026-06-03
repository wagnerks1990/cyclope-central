from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Agent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Installed endpoint agent registration for check-in and inventory telemetry."""

    __tablename__ = "agents"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    device_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), nullable=True
    )
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    install_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    device_secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="agents")
    device = relationship("Device", back_populates="agents")
    checkins = relationship("DeviceCheckin", back_populates="agent", cascade="all, delete-orphan")
