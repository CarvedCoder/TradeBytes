"""
Trading Schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TradeRequest(BaseModel):
    ticker: str = Field(..., max_length=10)
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)
    session_id: str | None = None  # optional simulation session context


class TradeResponse(BaseModel):
    trade_id: str
    ticker: str
    side: str
    quantity: float
    price: float
    total_value: float
    pnl: float | None = None
    pnl_pct: float | None = None
    # AI competitor result
    ai_trade: AITradeResult | None = None
    ai_explanation: str | None = None
    xp_earned: int = 0


class AITradeResult(BaseModel):
    side: str
    quantity: float
    price: float
    predicted_direction: str  # "up" or "down"
    confidence: float
    expected_return: float


class TradeHistory(BaseModel):
    trade_id: str
    ticker: str
    side: str
    quantity: float
    price: float
    total_value: float
    pnl: float | None = None
    pnl_pct: float | None = None
    trade_type: str
    ai_explanation: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
