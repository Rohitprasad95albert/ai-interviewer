"""
MongoDB connection lifecycle, managed via Motor (the async MongoDB driver).

The client is created once on FastAPI startup and closed on shutdown (see
app/main.py's lifespan handler) rather than opened per-request - this is the
standard pattern for connection pooling with Motor.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    client: AsyncIOMotorClient | None = None


mongodb = MongoDB()


async def connect_to_mongo() -> None:
    """Create the Motor client. Called once at application startup."""
    logger.info("Connecting to MongoDB at %s", settings.mongodb_uri)
    mongodb.client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
    )


async def close_mongo_connection() -> None:
    """Close the Motor client. Called once at application shutdown."""
    if mongodb.client is not None:
        mongodb.client.close()
        logger.info("MongoDB connection closed")


def get_database() -> AsyncIOMotorDatabase:
    """Return the application database handle for use in route/service code."""
    if mongodb.client is None:
        raise RuntimeError("MongoDB client is not initialized")
    return mongodb.client[settings.mongodb_db_name]


async def ping_database() -> bool:
    """Cheap connectivity check used by the /health endpoint."""
    if mongodb.client is None:
        return False
    try:
        await mongodb.client.admin.command("ping")
        return True
    except Exception:  # noqa: BLE001 - health check must never raise
        logger.exception("MongoDB ping failed")
        return False
