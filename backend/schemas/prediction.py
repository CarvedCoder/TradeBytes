"""
AI Prediction Schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    ticker: str
    horizon: str = "1d"  # 1d, 5d, etc.


class PredictionResponse(BaseModel):
    ticker: str
    horizon: str
    direction: str  # "up" or "down"
    direction_probability: float  # 0.0 to 1.0
    expected_return: float  # percentage
    confidence: float  # 0.0 to 1.0
    current_price: float
    predicted_price: float
    contributing_features: list[FeatureContribution]
    model_version: str


class FeatureContribution(BaseModel):
    feature: str
    importance: float
    value: float
    direction: str  # "bullish" or "bearish"


class PredictionExplanation(BaseModel):
    trade_id: str
    user_action: str
    ai_action: str
    ai_reasoning: str
    market_context: str
    sentiment_context: str
    outcome_comparison: str | None = None


class ModelPerformanceResponse(BaseModel):
    model_version: str
    overall_accuracy: float
    direction_accuracy: float
    avg_return: float
    sharpe_ratio: float
    ticker_performance: list[TickerPerformance] | None = None


class TickerPerformance(BaseModel):
    ticker: str
    accuracy: float
    avg_return: float
    total_predictions: int
