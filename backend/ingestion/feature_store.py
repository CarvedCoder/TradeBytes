"""
Feature Store.

Manages computed features for ML models:
- Stores pre-computed features in Redis for low-latency access
- Persists feature history in TimescaleDB
- Handles feature versioning for reproducibility
- Incremental computation for real-time updates
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import numpy as np
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.redis import RedisManager

logger = structlog.get_logger()


class FeatureStore:
    """Central feature store for ML pipeline."""

    FEATURE_PREFIX = "features:"
    FEATURE_VERSION = "v1"

    def __init__(self, redis: RedisManager, db: AsyncSession | None = None) -> None:
        self.redis = redis
        self.db = db

    async def store_features(
        self,
        entity_type: str,  # "ticker", "user"
        entity_id: str,     # "AAPL", "<user-uuid>"
        features: dict[str, float],
        ttl: int = 3600,
    ) -> None:
        """Store computed features in Redis."""
        key = f"{self.FEATURE_PREFIX}{self.FEATURE_VERSION}:{entity_type}:{entity_id}"
        payload = {
            "features": features,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "version": self.FEATURE_VERSION,
        }
        await self.redis.set(key, json.dumps(payload), expire=ttl)
        logger.debug("Stored features", entity_type=entity_type, entity_id=entity_id,
                      feature_count=len(features))

    async def get_features(
        self,
        entity_type: str,
        entity_id: str,
    ) -> dict[str, float] | None:
        """Retrieve features from store."""
        key = f"{self.FEATURE_PREFIX}{self.FEATURE_VERSION}:{entity_type}:{entity_id}"
        raw = await self.redis.get(key)
        if raw is None:
            return None
        payload = json.loads(raw)
        return payload.get("features")

    async def get_feature_vector(
        self,
        entity_type: str,
        entity_id: str,
        feature_names: list[str],
    ) -> np.ndarray | None:
        """Get features as ordered numpy array for model input."""
        features = await self.get_features(entity_type, entity_id)
        if features is None:
            return None
        vector = [features.get(name, 0.0) for name in feature_names]
        return np.array(vector, dtype=np.float32)

    async def store_batch(
        self,
        entity_type: str,
        features_map: dict[str, dict[str, float]],
        ttl: int = 3600,
    ) -> int:
        """Batch store features for multiple entities."""
        count = 0
        for entity_id, features in features_map.items():
            await self.store_features(entity_type, entity_id, features, ttl)
            count += 1
        return count

    async def get_feature_metadata(self, entity_type: str, entity_id: str) -> dict[str, Any] | None:
        """Get metadata about stored features (version, computation time, etc.)."""
        key = f"{self.FEATURE_PREFIX}{self.FEATURE_VERSION}:{entity_type}:{entity_id}"
        raw = await self.redis.get(key)
        if raw is None:
            return None
        payload = json.loads(raw)
        return {
            "computed_at": payload.get("computed_at"),
            "version": payload.get("version"),
            "feature_count": len(payload.get("features", {})),
        }

    async def invalidate(self, entity_type: str, entity_id: str) -> None:
        """Invalidate cached features (e.g., after new data arrives)."""
        key = f"{self.FEATURE_PREFIX}{self.FEATURE_VERSION}:{entity_type}:{entity_id}"
        await self.redis.delete(key)
