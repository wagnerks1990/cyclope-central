from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import auth_response
from app.api.schemas import AuthResponse, BootstrapSetupRequest, BootstrapStatusResponse
from app.core.bootstrap import bootstrap_status, create_first_owner, setup_required
from app.db.session import get_db

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.get("/status", response_model=BootstrapStatusResponse)
def get_bootstrap_status(db: Session = Depends(get_db)) -> BootstrapStatusResponse:
    has_org, has_owner = bootstrap_status(db)
    return BootstrapStatusResponse(
        has_organization=has_org,
        has_owner=has_owner,
        setup_required=not (has_org and has_owner),
    )


@router.post("/setup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def setup(payload: BootstrapSetupRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if not setup_required(db):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Bootstrap setup has already completed"
        )
    try:
        user, refresh_token = create_first_owner(
            db,
            organization_name=payload.organization_name,
            owner_name=payload.owner_name,
            owner_email=payload.owner_email,
            owner_password=payload.owner_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    return auth_response(db, user, refresh_token)
