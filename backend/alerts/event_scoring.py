"""Event scoring primitives for drastic market event detection.

The scoring layer is intentionally light: it only consumes pre-computed signals from
upstream components (news sentiment, market data, regime model output), then
normalizes and aggregates them into a calibrated event score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SignalSnapshot:
    """One aligned signal vector for a specific event timestamp + asset universe."""

    sentiment_intensity: float  # abs(finBERT polarity), expected [0, 1]
    volatility_zscore: float  # rolling sigma spike, typically [0, +inf)
    volume_zscore: float  # rolling volume spike, typically [0, +inf)
    regime_transition_prob: float  # probability of regime change [0, 1]
    abnormal_return_zscore: float  # |r_t - mu_t| / sigma_t, [0, +inf)
    asset_influence: float  # normalized cap-weight impact factor [0, 1]


@dataclass(frozen=True)
class EventScoreConfig:
    """Weighting and calibration settings.

    Weights are expected to sum to ~1.0. Penalties are used to reduce false positives.
    """

    w_sentiment: float = 0.18
    w_volatility: float = 0.17
    w_volume: float = 0.14
    w_regime: float = 0.19
    w_abnormal_return: float = 0.22
    w_influence: float = 0.10
    threshold: float = 0.68
    min_signals_above_half: int = 3


def _squash_positive_z(z: float, scale: float = 3.0) -> float:
    """Map non-negative z-score into [0,1) without heavy math libs."""

    if z <= 0:
        return 0.0
    return min(z / (z + scale), 0.999)


def normalize_signals(snapshot: SignalSnapshot) -> Dict[str, float]:
    """Convert mixed-range raw features to [0, 1] for a stable weighted sum."""

    return {
        "sentiment": min(max(snapshot.sentiment_intensity, 0.0), 1.0),
        "volatility": _squash_positive_z(snapshot.volatility_zscore),
        "volume": _squash_positive_z(snapshot.volume_zscore),
        "regime": min(max(snapshot.regime_transition_prob, 0.0), 1.0),
        "abnormal_return": _squash_positive_z(snapshot.abnormal_return_zscore),
        "influence": min(max(snapshot.asset_influence, 0.0), 1.0),
    }


def compute_event_score(snapshot: SignalSnapshot, config: EventScoreConfig) -> float:
    """Compute weighted multi-signal event score with anti-noise gating.

    Formula:
        EventScore = Σ_i (w_i * s_i) - penalty

    Penalty reduces single-signal spikes from generating false positives.
    """

    s = normalize_signals(snapshot)
    base = (
        config.w_sentiment * s["sentiment"]
        + config.w_volatility * s["volatility"]
        + config.w_volume * s["volume"]
        + config.w_regime * s["regime"]
        + config.w_abnormal_return * s["abnormal_return"]
        + config.w_influence * s["influence"]
    )

    active = sum(value >= 0.5 for value in s.values())
    if active >= config.min_signals_above_half:
        return min(base, 1.0)

    # Sparse activity penalty suppresses lone outliers.
    penalty = (config.min_signals_above_half - active) * 0.05
    return max(min(base - penalty, 1.0), 0.0)


def should_trigger_alert(score: float, config: EventScoreConfig) -> bool:
    return score >= config.threshold
