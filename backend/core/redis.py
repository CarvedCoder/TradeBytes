"""
Redis Connection Manager.

Provides async Redis client for caching, pub/sub, and streams.
"""

from __future__ import annotations

import redis.asyncio as aioredis
from redis.asyncio import Redis

from backend.core.config import get_settings

settings = get_settings()


class RedisManager:
    """Manages Redis connection lifecycle and provides utility methods."""

    def __init__(self) -> None:
        self._client: Redis | None = None
        self._pubsub_client: Redis | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
        self._pubsub_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close()
        if self._pubsub_client:
            await self._pubsub_client.close()

    @property
    def client(self) -> Redis:
        assert self._client is not None, "Redis not connected"
        return self._client

    @property
    def pubsub(self) -> Redis:
        assert self._pubsub_client is not None, "Redis pubsub not connected"
        return self._pubsub_client

    # ── Cache Helpers ──

    async def cache_get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def cache_set(self, key: str, value: str, ttl: int | None = None) -> None:
        await self.client.set(key, value, ex=ttl or settings.redis_cache_ttl)

    async def cache_delete(self, key: str) -> None:
        await self.client.delete(key)

    async def cache_exists(self, key: str) -> bool:
        return bool(await self.client.exists(key))

    # ── Stream Helpers (for ingestion pipeline) ──

    async def stream_add(self, stream: str, data: dict) -> str:
        return await self.client.xadd(stream, data)

    async def stream_read(
        self, stream: str, last_id: str = "0", count: int = 100, block: int = 0
    ) -> list:
        return await self.client.xread({stream: last_id}, count=count, block=block)

    # ── Pub/Sub Helpers ──

    async def publish(self, channel: str, message: str) -> int:
        return await self.client.publish(channel, message)


redis_manager = RedisManager()


async def get_redis() -> Redis:
    """FastAPI dependency: returns Redis client."""
    return redis_manager.client
