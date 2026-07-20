"""MongoDB connection via Motor + Beanie ODM."""
from motor.motor_asyncio import AsyncIOMotorClient

from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Return the shared Motor client (created on first init_db call)."""
    if _client is None:
        raise RuntimeError("MongoDB client not initialized — call init_db() on startup")
    return _client


async def init_db() -> None:
    """
    Connect to MongoDB and register Beanie document models.
    Beanie creates the declared indexes (unique account_id / tx_id, etc.)
    automatically, so there is no separate migration step.
    """
    global _client
    # Import here to avoid a circular import (models import Base-free Documents,
    # but importing them at module load would pull the whole app graph in early).
    from beanie import init_beanie

    from app.models.account import Account
    from app.models.transaction import Transaction

    _client = AsyncIOMotorClient(settings.mongo_uri)
    await init_beanie(
        database=_client[settings.mongo_db],
        document_models=[Account, Transaction],
    )


async def close_db() -> None:
    """Close the Motor client on shutdown."""
    global _client
    if _client is not None:
        _client.close()
        _client = None
