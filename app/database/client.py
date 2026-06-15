from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def close_client() -> None:
    """Close the client and reset the global so a fresh one is created next time."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def get_db() -> AsyncIOMotorDatabase:
    return get_client()[settings.database_name]

