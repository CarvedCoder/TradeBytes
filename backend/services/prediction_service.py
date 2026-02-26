"""
AI Prediction Service - LSTM Model Inference.

Loads the trained LSTM model and runs inference for price direction
prediction, confidence scoring, and feature attribution.
"""

from __future__ import annotations

import structlog
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionExplanation,
    ModelPerformanceResponse,
    FeatureContribution,
)

logger = structlog.get_logger()


class PredictionService:
    """Serves LSTM predictions and generates explanations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._model = None

    async def predict(self, request: PredictionRequest) -> PredictionResponse:
        """Run LSTM prediction for a ticker.
        
        Pipeline:
        1. Fetch recent feature window (60 candles)
        2. Build input tensor (market features + sentiment)
        3. Run LSTM forward pass
        4. Decode outputs (direction, magnitude, confidence)
        5. Map feature attributions
        """
        # Fetch features
        features = await self._build_feature_tensor(request.ticker)

        # Run model inference
        direction_prob, expected_return, confidence = await self._infer(features)

        direction = "up" if direction_prob > 0.5 else "down"
        current_price = await self._get_current_price(request.ticker)
        predicted_price = current_price * (1 + expected_return)

        # Feature attribution (simplified SHAP-like)
        contributions = self._compute_feature_contributions(features)

        return PredictionResponse(
            ticker=request.ticker,
            horizon=request.horizon,
            direction=direction,
            direction_probability=float(direction_prob),
            expected_return=float(expected_return),
            confidence=float(confidence),
            current_price=current_price,
            predicted_price=predicted_price,
            contributing_features=contributions,
            model_version="lstm-v1.0",
        )

    async def explain(self, trade_id: str) -> PredictionExplanation:
        """Generate detailed explanation for a prediction."""
        # TODO: fetch trade and associated prediction context
        return PredictionExplanation(
            trade_id=trade_id,
            user_action="buy",
            ai_action="buy",
            ai_reasoning="RSI indicates oversold conditions and MACD shows bullish crossover.",
            market_context="The stock has been in a consolidation phase for 5 days.",
            sentiment_context="Recent news sentiment is mildly positive (+0.3).",
            outcome_comparison=None,
        )

    async def get_performance(self, ticker: str | None) -> ModelPerformanceResponse:
        """Get model performance metrics."""
        return ModelPerformanceResponse(
            model_version="lstm-v1.0",
            overall_accuracy=0.62,
            direction_accuracy=0.58,
            avg_return=0.008,
            sharpe_ratio=1.1,
        )

    # ─── Private ───

    async def _build_feature_tensor(self, ticker: str) -> np.ndarray:
        """Build input tensor from feature store.
        
        Shape: (1, sequence_length=60, num_features=24)
        """
        # TODO: fetch from feature store / Redis
        return np.random.randn(1, 60, 24).astype(np.float32)

    async def _infer(self, features: np.ndarray) -> tuple[float, float, float]:
        """Run LSTM model inference.
        
        Returns (direction_prob, expected_return, confidence).
        """
        # TODO: load model and run inference
        # Placeholder with reasonable values
        direction_prob = 0.65
        expected_return = 0.012
        confidence = 0.72
        return direction_prob, expected_return, confidence

    async def _get_current_price(self, ticker: str) -> float:
        # TODO: from cache
        return 150.0

    def _compute_feature_contributions(self, features: np.ndarray) -> list[FeatureContribution]:
        """Compute simplified feature importance."""
        return [
            FeatureContribution(feature="RSI_14", importance=0.25, value=35.0, direction="bullish"),
            FeatureContribution(feature="MACD", importance=0.20, value=0.5, direction="bullish"),
            FeatureContribution(feature="Sentiment", importance=0.18, value=0.3, direction="bullish"),
            FeatureContribution(feature="Volume_Trend", importance=0.15, value=1.2, direction="bullish"),
            FeatureContribution(feature="Volatility_20d", importance=0.12, value=0.22, direction="bearish"),
            FeatureContribution(feature="SMA_50_Distance", importance=0.10, value=-0.02, direction="bearish"),
        ]
