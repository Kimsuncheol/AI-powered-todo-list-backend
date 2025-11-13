import redis.asyncio as redis

from app.core.config import settings


class RedisClient:
    _client: redis.Redis | None = None

    @classmethod
    def get_client(cls) -> redis.Redis:
        if cls._client is None:
            cls._client = redis.from_url(settings.redis_url, decode_responses=True)
        return cls._client


async def get_redis() -> redis.Redis:
    yield RedisClient.get_client()
