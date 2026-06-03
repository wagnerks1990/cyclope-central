import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured-friendly console logging for containers."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
