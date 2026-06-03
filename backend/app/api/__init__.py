from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.agent import router as agent_router
from app.api.alerts import router as alerts_router
from app.api.dashboard import router as dashboard_router
from app.api.devices import router as devices_router
from app.api.jobs import router as jobs_router
from app.api.notifications import router as notifications_router
from app.core.config import settings
from app.core.security import get_current_user_stub
from app.db.session import get_db

router = APIRouter()


@router.get("/health", tags=["platform"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    """Return service and database health for container orchestration checks."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@router.get("/version", tags=["platform"])
def version() -> dict[str, str]:
    """Expose immutable build/version metadata for operators."""
    return {"name": settings.project_name, "version": settings.app_version}


@router.get("/auth/session", tags=["auth"])
def session_stub(
    current_user: dict[str, str] = Depends(get_current_user_stub),
) -> dict[str, object]:
    """JWT authentication extension point; validates token plumbing without login flows yet."""
    return {"authenticated": True, "user": current_user}


router.include_router(alerts_router)
router.include_router(dashboard_router)
router.include_router(agent_router)
router.include_router(devices_router)
router.include_router(jobs_router)
router.include_router(notifications_router)
