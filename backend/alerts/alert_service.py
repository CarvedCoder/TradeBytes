"""Async alert persistence + integration hooks for downstream modules."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Dict

from .shock_detector import AlertRecord

logger = logging.getLogger("alerts.alert_service")


class AlertService:
    def __init__(self, db_pool: Any, redis_client: Any, redis_channel: str = "alerts.market.drastic"):
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.redis_channel = redis_channel

    async def persist_alert(self, alert: AlertRecord) -> None:
        payload = asdict(alert)
        payload["type"] = alert.type.value
        payload["timestamp"] = alert.timestamp.isoformat()

        query = """
        INSERT INTO alerts (
            alert_id, ts, type, severity, affected_assets, summary,
            confidence_score, event_score, raw_payload
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                query,
                alert.alert_id,
                alert.timestamp,
                alert.type.value,
                alert.severity,
                alert.affected_assets,
                alert.summary,
                alert.confidence_score,
                alert.event_score,
                json.dumps(payload),
            )

    async def publish_alert(self, alert: AlertRecord) -> None:
        payload = asdict(alert)
        payload["type"] = alert.type.value
        payload["timestamp"] = alert.timestamp.isoformat()
        await self.redis_client.publish(self.redis_channel, json.dumps(payload))

    async def append_audit(self, alert: AlertRecord, trace_id: str, source_event_id: str) -> None:
        query = """
        INSERT INTO alert_audit (alert_id, trace_id, source_event_id, created_at)
        VALUES ($1,$2,$3,now())
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(query, alert.alert_id, trace_id, source_event_id)

    async def process_alert(self, alert: AlertRecord, trace_id: str, source_event_id: str) -> None:
        logger.info(
            "alert.generated",
            extra={
                "alert_id": alert.alert_id,
                "trace_id": trace_id,
                "event_score": alert.event_score,
                "severity": alert.severity,
                "type": alert.type.value,
            },
        )
        await self.persist_alert(alert)
        await self.publish_alert(alert)
        await self.append_audit(alert, trace_id=trace_id, source_event_id=source_event_id)


async def risk_context_message(exposure_weight: float, ticker: str) -> Dict[str, Any]:
    if exposure_weight > 0.30:
        return {
            "ticker": ticker,
            "level": "WARNING",
            "message": f"Portfolio exposure to {ticker} is {exposure_weight:.0%}; consider hedge/rebalance.",
        }
    return {"ticker": ticker, "level": "INFO", "message": "Exposure within normal range."}
