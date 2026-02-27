"""Async alert persistence + integration hooks for downstream modules.

Adapted to the TradeBytes stack:
  - SQLAlchemy AsyncSession (not raw asyncpg)
  - RedisManager from backend.core.redis
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.redis import RedisManager
from backend.models.alerts import Alert, AlertAudit
from backend.services.alerts.shock_detector import AlertRecord

logger = structlog.get_logger("alerts.alert_service")


class AlertService:
    """Persist, publish, and audit market alerts."""

    def __init__(
        self,
        db: AsyncSession,
        redis: RedisManager,
        redis_channel: str = "alerts.market.drastic",
    ) -> None:
        self.db = db
        self.redis = redis
        self.redis_channel = redis_channel

    # ── Persistence ──────────────────────────────────────────────────────────

    async def persist_alert(self, alert: AlertRecord) -> None:
        """Insert an alert row via the ORM model."""
        payload = asdict(alert)
        payload["type"] = alert.type.value
        payload["timestamp"] = alert.timestamp.isoformat()

        row = Alert(
            alert_id=alert.alert_id,
            ts=alert.timestamp,
            type=alert.type.value,
            severity=alert.severity,
            affected_assets=alert.affected_assets,
            summary=alert.summary,
            confidence_score=alert.confidence_score,
            event_score=alert.event_score,
            raw_payload=payload,
        )
        self.db.add(row)
        await self.db.flush()

    # ── Redis Pub/Sub ────────────────────────────────────────────────────────

    async def publish_alert(self, alert: AlertRecord) -> None:
        """Publish alert to Redis channel for real-time consumers."""
        payload = asdict(alert)
        payload["type"] = alert.type.value
        payload["timestamp"] = alert.timestamp.isoformat()
        await self.redis.publish(self.redis_channel, json.dumps(payload, default=str))

    # ── Audit Trail ──────────────────────────────────────────────────────────

    async def append_audit(self, alert: AlertRecord, trace_id: str, source_event_id: str) -> None:
        row = AlertAudit(
            alert_id=alert.alert_id,
            trace_id=trace_id,
            source_event_id=source_event_id,
        )
        self.db.add(row)
        await self.db.flush()

    # ── Composite ────────────────────────────────────────────────────────────

    async def process_alert(
        self, alert: AlertRecord, trace_id: str, source_event_id: str
    ) -> None:
        """Full alert pipeline: log → persist → publish → audit."""
        logger.info(
            "alert.generated",
            alert_id=alert.alert_id,
            trace_id=trace_id,
            event_score=alert.event_score,
            severity=alert.severity,
            type=alert.type.value,
        )
        await self.persist_alert(alert)
        await self.publish_alert(alert)
        await self.append_audit(alert, trace_id=trace_id, source_event_id=source_event_id)

    # ── Query helpers (used by the API endpoints) ────────────────────────────

    async def get_history(self, limit: int = 100) -> list[dict]:
        from sqlalchemy import select, desc
        stmt = (
            select(Alert)
            .order_by(desc(Alert.ts))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "alert_id": r.alert_id,
                "ts": r.ts.isoformat() if r.ts else None,
                "type": r.type,
                "severity": r.severity,
                "affected_assets": r.affected_assets,
                "summary": r.summary,
                "confidence_score": r.confidence_score,
                "event_score": r.event_score,
            }
            for r in rows
        ]

    async def get_by_id(self, alert_id: str) -> dict | None:
        from sqlalchemy import select
        stmt = select(Alert).where(Alert.alert_id == alert_id)
        result = await self.db.execute(stmt)
        r = result.scalar_one_or_none()
        if r is None:
            return None
        return {
            "alert_id": r.alert_id,
            "ts": r.ts.isoformat() if r.ts else None,
            "type": r.type,
            "severity": r.severity,
            "affected_assets": r.affected_assets,
            "summary": r.summary,
            "confidence_score": r.confidence_score,
            "event_score": r.event_score,
            "raw_payload": r.raw_payload,
        }


async def risk_context_message(exposure_weight: float, ticker: str) -> Dict[str, Any]:
    """Simple portfolio-exposure heuristic used by downstream risk panels."""
    if exposure_weight > 0.30:
        return {
            "ticker": ticker,
            "level": "WARNING",
            "message": f"Portfolio exposure to {ticker} is {exposure_weight:.0%}; consider hedge/rebalance.",
        }
    return {"ticker": ticker, "level": "INFO", "message": "Exposure within normal range."}
