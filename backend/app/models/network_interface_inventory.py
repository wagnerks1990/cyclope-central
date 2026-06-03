from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class NetworkInterfaceInventory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Latest read-only network adapter inventory for a device."""

    __tablename__ = "network_interface_inventories"

    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    mac_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_addresses: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    device = relationship("Device")
