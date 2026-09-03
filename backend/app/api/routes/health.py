"""Health check endpoint - used by the frontend dashboard and by ops/monitoring."""

from fastapi import APIRouter

from app.core.config import settings
from app.db.mongodb import ping_database

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    Report whether the API process is up and whether it can reach MongoDB.

    Returns 200 even when the database is unreachable (status becomes
    "degraded") so callers can distinguish "API is down" from "API is up but
    DB is unavailable" without a failed request.
    """
    db_connected = await ping_database()
    return {
        "status": "ok" if db_connected else "degraded",
        "environment": settings.environment,
        "database": "connected" if db_connected else "unavailable",
    }
