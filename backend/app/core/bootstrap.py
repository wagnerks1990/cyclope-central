from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, issue_refresh_token
from app.models.organization import Organization
from app.models.user import User


def validate_strong_password(password: str) -> None:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters long")
    checks = [
        any(char.islower() for char in password),
        any(char.isupper() for char in password),
        any(char.isdigit() for char in password),
        any(not char.isalnum() for char in password),
    ]
    if sum(checks) < 3:
        raise ValueError("Password must include at least three character classes")


def bootstrap_status(db: Session) -> tuple[bool, bool]:
    organization_count = db.scalar(select(func.count()).select_from(Organization)) or 0
    owner_count = (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "owner", User.is_active.is_(True))
        )
        or 0
    )
    return organization_count > 0, owner_count > 0


def setup_required(db: Session) -> bool:
    has_org, has_owner = bootstrap_status(db)
    return not (has_org and has_owner)


def create_first_owner(
    db: Session,
    *,
    organization_name: str,
    owner_email: str,
    owner_password: str,
    owner_name: str | None = None,
) -> tuple[User, str]:
    if not setup_required(db):
        raise RuntimeError("Bootstrap setup has already completed")
    validate_strong_password(owner_password)
    slug = _slugify(organization_name)
    org = Organization(name=organization_name, slug=slug)
    db.add(org)
    db.flush()
    user = User(
        organization_id=org.id,
        email=owner_email.lower(),
        hashed_password=hash_password(owner_password),
        role="owner",
        is_active=True,
    )
    db.add(user)
    db.flush()
    refresh_token = issue_refresh_token(db, user)
    return user, refresh_token


def _slugify(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")
    return "-".join(part for part in slug.split("-") if part) or "default"
