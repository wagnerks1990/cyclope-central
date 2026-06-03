from fastapi import FastAPI

from app.api import router
from app.core.config import settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create the FastAPI application with security-first defaults."""
    configure_logging()
    application = FastAPI(
        title=settings.project_name,
        version=settings.app_version,
        docs_url="/docs" if settings.enable_openapi else None,
        redoc_url="/redoc" if settings.enable_openapi else None,
    )
    application.include_router(router, prefix=settings.api_prefix)
    return application


app = create_app()
