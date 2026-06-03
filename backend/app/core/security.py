import hashlib
import hmac
import os
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.token_hashing import hash_token, verify_token
from app.db.session import get_db
from app.models.organization import Organization
from app.models.refresh_token import RefreshToken
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)

ROLES = {"viewer", "technician", "admin", "owner"}
ROLE_PERMISSIONS = {
    "viewer": {"dashboard:read", "devices:read", "alerts:read", "jobs:read"},
    "technician": {
        "dashboard:read",
        "devices:read",
        "alerts:read",
        "alerts:acknowledge",
        "jobs:read",
        "jobs:create",
        "jobs:cancel",
    },
    "admin": {
        "dashboard:read",
        "devices:read",
        "alerts:read",
        "alerts:acknowledge",
        "jobs:read",
        "jobs:create",
        "jobs:cancel",
        "notifications:manage",
        "enrollment_tokens:manage",
    },
    "owner": {
        "dashboard:read",
        "devices:read",
        "alerts:read",
        "alerts:acknowledge",
        "jobs:read",
        "jobs:create",
        "jobs:cancel",
        "notifications:manage",
        "enrollment_tokens:manage",
        "users:manage",
        "organization:manage",
    },
}
ACCESS_TOKEN_MINUTES = 15
REFRESH_TOKEN_DAYS = 14


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return "pbkdf2_sha256$210000$" + salt.hex() + "$" + digest.hex()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def role_permissions(role: str) -> set[str]:
    return ROLE_PERMISSIONS.get(role, set())


def create_access_token(user: User) -> str:
    expires = now_utc() + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    payload = {
        "sub": str(user.id),
        "org": str(user.organization_id),
        "role": user.role,
        "type": "access",
        "exp": expires,
        "iat": now_utc(),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def issue_refresh_token(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(48)
    db.add(
        RefreshToken(
            organization_id=user.organization_id,
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now_utc() + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    return raw_token


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user_id = payload.get("sub")
    try:
        parsed_user_id = UUID(str(user_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        ) from exc
    user = db.get(User, parsed_user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return user


def require_role(*roles: str) -> Callable[[User], User]:
    def dependency(user: User = Depends(require_authenticated_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency


def require_permission(permission: str) -> Callable[[User], User]:
    def dependency(user: User = Depends(require_authenticated_user)) -> User:
        if permission not in role_permissions(user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission"
            )
        return user

    return dependency


def get_current_organization(
    user: User = Depends(require_authenticated_user), db: Session = Depends(get_db)
) -> Organization:
    organization = db.get(Organization, user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization unavailable"
        )
    return organization


def find_valid_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    candidates = db.scalars(
        select(RefreshToken).where(
            RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now_utc()
        )
    ).all()
    return next((token for token in candidates if verify_token(raw_token, token.token_hash)), None)


def get_current_user_stub(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    user = require_authenticated_user(credentials, db)
    return {"subject": str(user.id), "email": user.email, "role": user.role}
