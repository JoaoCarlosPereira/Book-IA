"""Health checks for Redis broker and Celery workers."""

from __future__ import annotations

import logging
from typing import Any

import redis
from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)


def check_redis() -> dict[str, Any]:
    """Ping Redis; return ok or error payload."""
    try:
        client = redis.from_url(settings.redis_url, socket_connect_timeout=3)
        client.ping()
        return {"redis": "ok"}
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        return {"redis": "error", "detail": str(exc)}


def check_celery(celery_app: Celery) -> dict[str, Any]:
    """Inspect active Celery workers; return ok with count or error."""
    try:
        inspect = celery_app.control.inspect(timeout=3.0)
        stats = inspect.stats() if inspect else None
        if not stats:
            return {
                "celery": "error",
                "detail": "Nenhum worker Celery respondeu",
                "worker_count": 0,
            }
        worker_count = len(stats)
        return {"celery": "ok", "worker_count": worker_count}
    except Exception as exc:
        logger.warning("Celery health check failed: %s", exc)
        return {
            "celery": "error",
            "detail": str(exc),
            "worker_count": 0,
        }
