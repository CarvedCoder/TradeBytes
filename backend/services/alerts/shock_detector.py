"""Shock / drastic-move detector and AlertRecord dataclass.

Defines the core data structures used by the alert pipeline and a simple
threshold-based detector that can be called from ingestion or scheduled tasks.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


class AlertType(str, enum.Enum):
    """Categories of market alerts."""

    PRICE_SHOCK = "price_shock"
    VOLUME_SPIKE = "volume_spike"
    SENTIMENT_SHIFT = "sentiment_shift"
    NEWS_EVENT = "news_event"
    VOLATILITY_SURGE = "volatility_surge"


@dataclass
class AlertRecord:
    """Immutable record produced each time the detector fires."""

    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    type: AlertType = AlertType.PRICE_SHOCK
    severity: str = "medium"           # low | medium | high | critical
    affected_assets: List[str] = field(default_factory=list)
    summary: str = ""
    confidence_score: float = 0.0      # 0-1
    event_score: float = 0.0           # composite score
    raw_payload: Dict[str, Any] = field(default_factory=dict)


class ShockDetector:
    """Simple threshold-based shock detector.

    Parameters
    ----------
    price_pct_threshold : float
        Absolute percentage move considered 'drastic' (e.g. 0.05 = ±5 %).
    volume_mult_threshold : float
        Volume must exceed the rolling average by this multiplier.
    """

    def __init__(
        self,
        price_pct_threshold: float = 0.05,
        volume_mult_threshold: float = 3.0,
    ) -> None:
        self.price_pct_threshold = price_pct_threshold
        self.volume_mult_threshold = volume_mult_threshold

    def evaluate(
        self,
        ticker: str,
        current_price: float,
        previous_close: float,
        current_volume: float,
        avg_volume: float,
        extra: Dict[str, Any] | None = None,
    ) -> AlertRecord | None:
        """Return an *AlertRecord* if thresholds are breached, else ``None``."""
        pct_change = (current_price - previous_close) / previous_close if previous_close else 0.0
        vol_ratio = current_volume / avg_volume if avg_volume else 0.0

        triggered = False
        alert_type = AlertType.PRICE_SHOCK
        severity = "medium"
        details: Dict[str, Any] = {
            "ticker": ticker,
            "price": current_price,
            "prev_close": previous_close,
            "pct_change": round(pct_change, 6),
            "volume": current_volume,
            "avg_volume": avg_volume,
            "vol_ratio": round(vol_ratio, 2),
        }
        if extra:
            details.update(extra)

        # ── Price shock ──
        if abs(pct_change) >= self.price_pct_threshold:
            triggered = True
            severity = "critical" if abs(pct_change) >= self.price_pct_threshold * 2 else "high"

        # ── Volume spike ──
        if vol_ratio >= self.volume_mult_threshold:
            triggered = True
            alert_type = AlertType.VOLUME_SPIKE if not triggered else AlertType.PRICE_SHOCK
            if severity not in ("high", "critical"):
                severity = "high" if vol_ratio >= self.volume_mult_threshold * 2 else "medium"

        if not triggered:
            return None

        confidence = min(1.0, (abs(pct_change) / self.price_pct_threshold) * 0.5 + (vol_ratio / self.volume_mult_threshold) * 0.5)
        event_score = abs(pct_change) * 100 + vol_ratio * 10

        return AlertRecord(
            type=alert_type,
            severity=severity,
            affected_assets=[ticker],
            summary=f"{ticker} moved {pct_change:+.2%} on {vol_ratio:.1f}× avg volume",
            confidence_score=round(confidence, 4),
            event_score=round(event_score, 4),
            raw_payload=details,
        )
