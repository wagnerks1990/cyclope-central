from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class NotificationDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Retryable notification delivery attempt for an alert/channel pair."""

    __tablename__ = "notification_deliveries"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    alert_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("alerts.id"), index=True)
    channel_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("notification_channels.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    alert = relationship("Alert")
    channel = relationship("NotificationChannel")
