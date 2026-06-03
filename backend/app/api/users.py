from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.auth import user_response
from app.api.schemas import UserCreateRequest, UserPatchRequest, UserResponse
from app.core.security import ROLES, hash_password, require_permission
from app.db.session import get_db
from app.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


def _require_same_org_user(db: Session, user_id: UUID, organization_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.get("", response_model=list[UserResponse])
def list_users(
    current: User = Depends(require_permission("users:manage")), db: Session = Depends(get_db)
) -> list[UserResponse]:
    users = db.scalars(
        select(User).where(User.organization_id == current.organization_id).order_by(User.email)
    ).all()
    return [user_response(user) for user in users]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    current: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    if payload.role not in ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    existing = db.scalar(select(User).where(User.email == payload.email.lower()))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    user = User(
        organization_id=current.organization_id,
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: UUID,
    payload: UserPatchRequest,
    current: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = _require_same_org_user(db, user_id, current.organization_id)
    if payload.role is not None:
        if payload.role not in ROLES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        user.role = payload.role
    if payload.email is not None:
        user.email = payload.email.lower()
    if payload.password is not None:
        user.hashed_password = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.post("/{user_id}/disable", response_model=UserResponse)
def disable_user(
    user_id: UUID,
    current: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = _require_same_org_user(db, user_id, current.organization_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user_response(user)


@router.post("/{user_id}/enable", response_model=UserResponse)
def enable_user(
    user_id: UUID,
    current: User = Depends(require_permission("users:manage")),
    db: Session = Depends(get_db),
) -> UserResponse:
    user = _require_same_org_user(db, user_id, current.organization_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user_response(user)
