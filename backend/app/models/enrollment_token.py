from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EnrollmentToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Hashed one-time or limited-use token for safe agent enrollment."""

    __tablename__ = "enrollment_tokens"

    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_uses: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    uses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    organization = relationship("Organization", back_populates="enrollment_tokens")
    created_by = relationship("User")
