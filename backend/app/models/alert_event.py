from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AlertEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable alert lifecycle event."""

    __tablename__ = "alert_events"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    alert_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("alerts.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    alert = relationship("Alert", back_populates="events")
