"""Pydantic schemas for the alert API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Single alert returned by the history / detail endpoints."""

    alert_id: str
    ts: str | None = None
    type: str
    severity: str
    affected_assets: List[str] = Field(default_factory=list)
    summary: str = ""
    confidence_score: float = 0.0
    event_score: float = 0.0
    raw_payload: Dict[str, Any] | None = None


class AlertHistoryResponse(BaseModel):
    """Paginated list of alerts."""

    alerts: List[AlertResponse]
    count: int


class RiskContextResponse(BaseModel):
    """Risk-exposure advisory."""

    ticker: str
    level: str
    message: str


class ShockEvaluateRequest(BaseModel):
    """Manual shock evaluation request body."""

    ticker: str
    current_price: float
    previous_close: float
    current_volume: float
    avg_volume: float
    extra: Dict[str, Any] | None = None


class ShockEvaluateResponse(BaseModel):
    """Result of a manual shock evaluation."""

    triggered: bool
    alert: AlertResponse | None = None
