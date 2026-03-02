from backend.alerts.event_scoring import EventScoreConfig, SignalSnapshot, compute_event_score
from backend.alerts.shock_detector import severity_from_score


def test_event_score_increases_with_multi_signal_strength():
    cfg = EventScoreConfig()
    low = SignalSnapshot(0.1, 0.1, 0.1, 0.1, 0.1, 0.1)
    high = SignalSnapshot(0.9, 4.0, 3.5, 0.8, 4.2, 0.9)
    assert compute_event_score(high, cfg) > compute_event_score(low, cfg)


def test_sparse_signal_penalty_applies():
    cfg = EventScoreConfig(min_signals_above_half=3)
    sparse = SignalSnapshot(0.9, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert compute_event_score(sparse, cfg) < cfg.threshold


def test_severity_boundaries():
    assert severity_from_score(0.70) == "LOW"
    assert severity_from_score(0.80) == "MEDIUM"
    assert severity_from_score(0.90) == "HIGH"
