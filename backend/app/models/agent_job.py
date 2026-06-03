from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AgentJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Safe predefined job assigned to an enrolled agent."""

    __tablename__ = "agent_jobs"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    device_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("devices.id"), index=True
    )
    assigned_agent_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)

    device = relationship("Device")
    assigned_agent = relationship("Agent")
    result = relationship("AgentJobResult", back_populates="job", uselist=False)
    events = relationship("AgentJobEvent", back_populates="job", cascade="all, delete-orphan")
