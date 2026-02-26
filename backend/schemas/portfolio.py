"""
Portfolio Schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


class PortfolioOverview(BaseModel):
    total_value: float
    cash_balance: float
    invested_value: float
    total_pnl: float
    total_pnl_pct: float
    positions: list[PositionInfo]
    allocation: list[AllocationSlice]


class PositionInfo(BaseModel):
    ticker: str
    shares: float
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float  # % of portfolio


class AllocationSlice(BaseModel):
    label: str  # ticker or "Cash"
    value: float
    percentage: float


class RiskMetrics(BaseModel):
    portfolio_volatility: float
    portfolio_beta: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    value_at_risk_95: float
    per_position: list[PositionRisk]


class PositionRisk(BaseModel):
    ticker: str
    volatility: float
    beta: float
    weight: float


class CorrelationMatrix(BaseModel):
    tickers: list[str]
    matrix: list[list[float]]


class DrawdownAnalysis(BaseModel):
    current_drawdown: float
    max_drawdown: float
    max_drawdown_duration_days: int
    recovery_time_days: int | None
    drawdown_series: list[DrawdownPoint]


class DrawdownPoint(BaseModel):
    date: str
    value: float
    drawdown: float


class AIPortfolioSuggestions(BaseModel):
    overall_assessment: str
    risk_level: str
    suggestions: list[PortfolioSuggestion]


class PortfolioSuggestion(BaseModel):
    type: str  # "rebalance", "hedge", "diversify", "reduce_risk"
    ticker: str | None = None
    action: str
    reason: str
    confidence: float
