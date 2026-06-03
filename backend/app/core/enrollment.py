from datetime import UTC, datetime, timedelta

from app.core.token_hashing import generate_secret, hash_token
from app.models.enrollment_token import EnrollmentToken


def build_enrollment_token(
    organization_id, *, ttl_hours: int = 24, max_uses: int = 1
) -> tuple[str, EnrollmentToken]:
    """Create a plaintext enrollment token once and a model containing only its hash."""
    plaintext = generate_secret()
    model = EnrollmentToken(
        organization_id=organization_id,
        token_hash=hash_token(plaintext),
        expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        max_uses=max_uses,
        uses=0,
    )
    return plaintext, model
