"""Pydantic schemas for all visualization endpoints"""
from pydantic import BaseModel
from typing import List, Optional, Dict
from enum import Enum

# ── Market / News ──────────────────────────────────────────
class OHLCV(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class SentimentPoint(BaseModel):
    timestamp: str
    score: float          # -1.0 to 1.0
    label: str            # "positive" | "negative" | "neutral"
    article_count: int

class NewsEvent(BaseModel):
    id: str
    timestamp: str
    headline: str
    source: str
    sentiment_score: float
    price_before: float
    price_after: float
    abnormal_return: float  # event-window excess return

class TimeseriesResponse(BaseModel):
    ticker: str
    interval: str
    candles: List[OHLCV]

class SentimentResponse(BaseModel):
    ticker: str
    data: List[SentimentPoint]

class EventsResponse(BaseModel):
    ticker: str
    events: List[NewsEvent]

# ── Portfolio ──────────────────────────────────────────────
class RiskMetrics(BaseModel):
    volatility_ann: float
    beta: float
    max_drawdown: float
    diversification_ratio: float
    sharpe_ratio: float
    sortino_ratio: float
    var_95: float
    cvar_95: float

class EquityPoint(BaseModel):
    date: str
    portfolio_value: float
    benchmark_value: float
    drawdown_pct: float

class AllocationItem(BaseModel):
    asset: str
    weight: float
    value: float
    sector: str

class CorrelationMatrix(BaseModel):
    assets: List[str]
    matrix: List[List[float]]  # NxN
    period_days: int

class PortfolioMetricsResponse(BaseModel):
    portfolio_id: str
    metrics: RiskMetrics
    allocation: List[AllocationItem]

class EquityCurveResponse(BaseModel):
    portfolio_id: str
    data: List[EquityPoint]

# ── Regime ─────────────────────────────────────────────────
class RegimeType(str, Enum):
    TRENDING    = "trending"
    VOLATILE    = "volatile"
    MEAN_REVERT = "mean_reverting"
    UNKNOWN     = "unknown"

class RegimeSegment(BaseModel):
    start: str
    end: str
    regime: RegimeType
    confidence: float

class RegimeProbPoint(BaseModel):
    timestamp: str
    p_trending: float
    p_volatile: float
    p_mean_revert: float
    dominant: RegimeType

class RegimeResponse(BaseModel):
    ticker: str
    price_data: List[OHLCV]
    segments: List[RegimeSegment]
    probabilities: List[RegimeProbPoint]
    transitions: List[dict]

# ── Trades ─────────────────────────────────────────────────
class TradeAction(str, Enum):
    BUY  = "buy"
    SELL = "sell"

class Trade(BaseModel):
    id: str
    timestamp: str
    action: TradeAction
    ticker: str
    price: float
    quantity: int
    pnl: Optional[float] = None
    ai_signal: Optional[str] = None
    is_mistake: bool = False
    mistake_reason: Optional[str] = None

class PnLPoint(BaseModel):
    timestamp: str
    cumulative_pnl: float
    trade_pnl: Optional[float] = None

class TradeSessionResponse(BaseModel):
    session_id: str
    ticker: str
    candles: List[OHLCV]
    trades: List[Trade]
    pnl_timeline: List[PnLPoint]
    session_summary: dict