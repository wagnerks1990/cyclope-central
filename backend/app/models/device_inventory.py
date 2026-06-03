from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeviceInventory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Latest read-only hardware and operating system inventory for a device."""

    __tablename__ = "device_inventories"

    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), unique=True, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)
    operating_system: Mapped[str] = mapped_column(String(128), nullable=False)
    os_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    os_build: Mapped[str | None] = mapped_column(String(128), nullable=True)
    architecture: Mapped[str | None] = mapped_column(String(64), nullable=True)
    agent_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cpu_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_total_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    bios_vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bios_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    system_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inventory_refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    device = relationship("Device")
