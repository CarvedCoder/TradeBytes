"""Drastic Event Alert System package."""

from .event_scoring import EventScoreConfig, SignalSnapshot, compute_event_score
from .shock_detector import AlertRecord, AlertType, detect_drastic_event

__all__ = [
    "EventScoreConfig",
    "SignalSnapshot",
    "compute_event_score",
    "AlertRecord",
    "AlertType",
    "detect_drastic_event",
]
