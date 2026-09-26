import logging
import sys

from app.core.config import settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure structured logging for the application (idempotent)."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level = logging.DEBUG if settings.app_debug else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
