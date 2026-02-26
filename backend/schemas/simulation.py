"""
Simulation Schemas - Replay Engine models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class SimulationCreateRequest(BaseModel):
    ticker: str = Field(..., max_length=10)
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    initial_capital: float = Field(default=10000.0, gt=0)
    playback_speed: float = Field(default=1.0, ge=0.25, le=10.0)


class SimulationCreateResponse(BaseModel):
    session_id: str
    ticker: str
    total_candles: int
    initial_capital: float
    ws_url: str  # WebSocket URL for candle streaming


class SimulationState(BaseModel):
    session_id: str
    ticker: str
    status: str
    current_candle_index: int
    total_candles: int
    current_price: float
    cash_balance: float
    shares_held: float
    portfolio_value: float
    user_pnl: float
    user_pnl_pct: float
    ai_pnl: float
    ai_pnl_pct: float
    playback_speed: float


class SimulationControlRequest(BaseModel):
    action: str = Field(..., pattern="^(play|pause|speed|skip)$")
    speed: float | None = None
    skip_to: int | None = None


class SimulationTradeRequest(BaseModel):
    side: str = Field(..., pattern="^(buy|sell)$")
    quantity: float = Field(..., gt=0)


class SimulationTradeResponse(BaseModel):
    trade_id: str
    side: str
    quantity: float
    price: float
    cash_balance: float
    shares_held: float
    portfolio_value: float
    pnl: float
    ai_action: str  # "buy", "sell", "hold"
    ai_explanation: str


class SimulationResult(BaseModel):
    session_id: str
    ticker: str
    duration_candles: int
    user_final_value: float
    user_pnl: float
    user_pnl_pct: float
    user_trades_count: int
    ai_final_value: float
    ai_pnl: float
    ai_pnl_pct: float
    ai_trades_count: int
    winner: str  # "user" or "ai"
    xp_earned: int
    explanation: str


class AvailableTickers(BaseModel):
    tickers: list[TickerInfo]


class TickerInfo(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    earliest_date: str
    latest_date: str
    total_candles: int
