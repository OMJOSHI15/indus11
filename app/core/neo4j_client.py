"""Neo4j async driver wrapper."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver

from app.config import settings

_driver: AsyncDriver | None = None


def get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def neo4j_session() -> AsyncGenerator:
    """Async context manager yielding a Neo4j session."""
    async with get_driver().session() as session:
        yield session


async def ensure_indexes() -> None:
    """Create Neo4j indexes on startup."""
    async with neo4j_session() as session:
        await session.run("CREATE INDEX account_id IF NOT EXISTS FOR (a:Account) ON (a.account_id)")
        await session.run("CREATE INDEX tx_id IF NOT EXISTS FOR (t:Transaction) ON (t.tx_id)")
        await session.run("CREATE INDEX device_id IF NOT EXISTS FOR (d:Device) ON (d.device_id)")
