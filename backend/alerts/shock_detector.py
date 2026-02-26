"""High-level detector that classifies market shocks from event scores."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List
from uuid import uuid4

from .event_scoring import EventScoreConfig, SignalSnapshot, compute_event_score, should_trigger_alert


class AlertType(str, Enum):
    NEWS_SHOCK = "NEWS_SHOCK"
    VOLATILITY_SPIKE = "VOLATILITY_SPIKE"
    REGIME_SHIFT = "REGIME_SHIFT"
    MARKET_WIDE_EVENT = "MARKET_WIDE_EVENT"


@dataclass(frozen=True)
class AlertRecord:
    alert_id: str
    timestamp: datetime
    type: AlertType
    severity: str
    affected_assets: List[str]
    summary: str
    confidence_score: float
    event_score: float


def classify_alert_type(snapshot: SignalSnapshot, affected_assets_count: int) -> AlertType:
    if affected_assets_count >= 8 and snapshot.asset_influence > 0.7:
        return AlertType.MARKET_WIDE_EVENT
    if snapshot.regime_transition_prob >= 0.65:
        return AlertType.REGIME_SHIFT
    if snapshot.volatility_zscore >= 3.0:
        return AlertType.VOLATILITY_SPIKE
    return AlertType.NEWS_SHOCK


def severity_from_score(event_score: float) -> str:
    if event_score >= 0.85:
        return "HIGH"
    if event_score >= 0.72:
        return "MEDIUM"
    return "LOW"


def summarize(alert_type: AlertType, affected_assets: List[str]) -> str:
    assets_label = ", ".join(affected_assets[:4]) + ("..." if len(affected_assets) > 4 else "")
    return f"{alert_type.value} detected across {len(affected_assets)} assets: {assets_label}"


def detect_drastic_event(
    snapshot: SignalSnapshot,
    affected_assets: List[str],
    config: EventScoreConfig | None = None,
) -> AlertRecord | None:
    cfg = config or EventScoreConfig()
    score = compute_event_score(snapshot, cfg)
    if not should_trigger_alert(score, cfg):
        return None

    alert_type = classify_alert_type(snapshot, len(affected_assets))
    return AlertRecord(
        alert_id=str(uuid4()),
        timestamp=datetime.now(tz=timezone.utc),
        type=alert_type,
        severity=severity_from_score(score),
        affected_assets=affected_assets,
        summary=summarize(alert_type, affected_assets),
        confidence_score=min(max(score + 0.05, 0.0), 1.0),
        event_score=score,
    )
