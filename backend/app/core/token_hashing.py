import hmac
import secrets
from hashlib import sha256

from app.core.config import settings


def generate_secret() -> str:
    """Generate a high-entropy URL-safe token for enrollment and device credentials."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Hash a token with an application pepper; never persist plaintext tokens."""
    return hmac.new(settings.token_hash_pepper.encode(), token.encode(), sha256).hexdigest()


def verify_token(token: str, token_hash: str) -> bool:
    """Constant-time token hash comparison."""
    return hmac.compare_digest(hash_token(token), token_hash)
