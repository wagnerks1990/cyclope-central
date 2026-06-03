from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    OrganizationResponse,
    RefreshRequest,
    UserResponse,
)
from app.core.security import (
    create_access_token,
    find_valid_refresh_token,
    issue_refresh_token,
    now_utc,
    require_authenticated_user,
    role_permissions,
    verify_password,
)
from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def org_response(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(id=organization.id, name=organization.name, slug=organization.slug)


def auth_response(db: Session, user: User, refresh_token: str) -> AuthResponse:
    organization = db.get(Organization, user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization unavailable"
        )
    return AuthResponse(
        access_token=create_access_token(user),
        refresh_token=refresh_token,
        user=user_response(user),
        organization=org_response(organization),
        permissions=sorted(role_permissions(user.role)),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    refresh_token = issue_refresh_token(db, user)
    db.commit()
    return auth_response(db, user, refresh_token)


@router.post("/refresh", response_model=AuthResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> AuthResponse:
    token = find_valid_refresh_token(db, payload.refresh_token)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    token.revoked_at = now_utc()
    new_refresh = issue_refresh_token(db, user)
    db.commit()
    return auth_response(db, user, new_refresh)


@router.post("/logout")
def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    token = find_valid_refresh_token(db, payload.refresh_token)
    if token is not None:
        token.revoked_at = now_utc()
        db.commit()
    return {"status": "ok"}


@router.get("/me", response_model=CurrentUserResponse)
def current_user(
    user: User = Depends(require_authenticated_user), db: Session = Depends(get_db)
) -> CurrentUserResponse:
    organization = db.get(Organization, user.organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Organization unavailable"
        )
    return CurrentUserResponse(
        user=user_response(user),
        organization=org_response(organization),
        permissions=sorted(role_permissions(user.role)),
    )
