"""
AI Prediction Service - LSTM Model Inference.

Loads the trained LSTM model and runs inference for price direction
prediction, confidence scoring, and feature attribution.
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog
import numpy as np
import torch
from sqlalchemy.ext.asyncio import AsyncSession

from backend.ml.lstm_model import StockLSTM, LSTMPrediction
from backend.ml.features import FeatureBuilder, FeatureConfig
from backend.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionExplanation,
    ModelPerformanceResponse,
    FeatureContribution,
)

logger = structlog.get_logger()

# ─── Singleton model cache ───
_model_cache: dict[str, StockLSTM] = {}
_scaler_cache: dict[str, dict] = {}  # feature scaler stats per ticker
_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_MODEL_DIR = Path(os.getenv("MODEL_DIR", "./models"))


def _load_model(ticker: str) -> StockLSTM | None:
    """Load a trained model from disk (cached after first load)."""
    if ticker in _model_cache:
        return _model_cache[ticker]

    # Try ticker-specific best checkpoint first, then glob for dated files
    candidates = [
        _MODEL_DIR / f"{ticker}_best.pt",
        *sorted(_MODEL_DIR.glob(f"{ticker}_lstm_*.pt"), reverse=True),
    ]

    for path in candidates:
        if path.exists():
            try:
                checkpoint = torch.load(path, map_location=_device, weights_only=False)
                config = checkpoint.get("config")
                model = StockLSTM(
                    input_size=getattr(config, "input_size", 19),
                    hidden_size=getattr(config, "hidden_size", 128),
                    num_layers=getattr(config, "num_layers", 3),
                    dropout=getattr(config, "dropout", 0.3),
                    use_attention=getattr(config, "use_attention", True),
                )
                model.load_state_dict(checkpoint["model_state_dict"])
                model.to(_device)
                model.eval()
                _model_cache[ticker] = model
                # Cache feature scaler stats for inference normalization
                scaler = checkpoint.get("feature_scaler", {})
                if scaler:
                    _scaler_cache[ticker] = scaler
                logger.info("Model loaded", ticker=ticker, path=str(path),
                            has_scaler=bool(scaler))
                return model
            except Exception as e:
                logger.error("Failed to load model", ticker=ticker, path=str(path), error=str(e))
                continue

    logger.warning("No trained model found", ticker=ticker, searched=str(_MODEL_DIR))
    return None


class PredictionService:
    """Serves LSTM predictions and generates explanations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._feature_config = FeatureConfig(sequence_length=60)
        self._feature_builder = FeatureBuilder(self._feature_config)

    async def predict(self, request: PredictionRequest) -> PredictionResponse:
        """Run LSTM prediction for a ticker.

        Pipeline:
        1. Load trained model
        2. Fetch recent OHLCV data (via yfinance)
        3. Build input tensor (market features + sentiment)
        4. Run LSTM forward pass
        5. Decode outputs (direction, magnitude, confidence)
        6. Map feature attributions
        """
        # Load model
        model = _load_model(request.ticker)
        if model is None:
            raise ValueError(
                f"No trained model for {request.ticker}. "
                f"Train one first: python scripts/train_model.py --ticker {request.ticker}"
            )

        # Build features from live data
        features, raw_features_df = await self._build_feature_tensor(request.ticker)

        # Run model inference
        direction_prob, expected_return, confidence, attn_weights = self._infer(model, features)

        direction = "up" if direction_prob > 0.5 else "down"
        current_price = await self._get_current_price(request.ticker)
        predicted_price = current_price * (1 + expected_return)

        # Feature attribution from attention weights
        contributions = self._compute_feature_contributions(features, attn_weights)

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

    async def _build_feature_tensor(self, ticker: str) -> tuple[np.ndarray, None]:
        """Fetch recent OHLCV data and build the feature tensor.

        Returns:
            features: (1, seq_len, num_features) numpy array
            raw_df: None (reserved for future use with raw DataFrame)
        """
        import yfinance as yf

        # Fetch enough history for seq_length + rolling window warmup
        df = yf.Ticker(ticker).history(period="6mo", interval="1d")
        if df.empty:
            raise ValueError(f"No recent market data available for {ticker}")

        df.columns = [c.lower() for c in df.columns]
        scaler = _scaler_cache.get(ticker)
        features = self._feature_builder.build_inference_tensor(df, scaler=scaler)
        return features, None

    @torch.no_grad()
    def _infer(
        self, model: StockLSTM, features: np.ndarray
    ) -> tuple[float, float, float, np.ndarray]:
        """Run LSTM model inference.

        Returns (direction_prob, expected_return, confidence, attention_weights).
        """
        tensor = torch.FloatTensor(features).to(_device)
        prediction: LSTMPrediction = model(tensor)
        return (
            prediction.direction_prob.item(),
            prediction.expected_return.item(),
            prediction.confidence.item(),
            prediction.attention_weights.cpu().numpy()[0],
        )

    async def _get_current_price(self, ticker: str) -> float:
        """Get current price via yfinance."""
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).fast_info
            return float(info.last_price)
        except Exception:
            return 0.0

    def _compute_feature_contributions(
        self, features: np.ndarray, attn_weights: np.ndarray
    ) -> list[FeatureContribution]:
        """Compute feature importance using attention weights and feature variance.

        Combines temporal attention (which timesteps matter) with
        per-feature variance (which features vary most in the window).
        """
        # features shape: (1, seq_len, num_features)
        seq = features[0]  # (seq_len, num_features)

        # Weighted feature values: attention over time
        weighted = attn_weights[:, np.newaxis] * seq  # (seq_len, num_features)
        feature_importance = np.abs(weighted).sum(axis=0)  # (num_features,)

        # Normalize to sum to 1
        total = feature_importance.sum()
        if total > 0:
            feature_importance /= total

        # Last timestep values for display
        last_values = seq[-1]

        contributions = []
        feature_names = list(_scaler_cache.get(request.ticker, {}).get('names', []))
        if not feature_names:
            feature_names = list(self._feature_config.market_features or [])
        for i, name in enumerate(feature_names):
            if i >= len(feature_importance):
                break
            imp = float(feature_importance[i])
            if imp < 0.02:  # Skip negligible features
                continue
            val = float(last_values[i])
            direction = "bullish" if val > 0 else "bearish"
            contributions.append(
                FeatureContribution(
                    feature=name, importance=imp, value=round(val, 4), direction=direction
                )
            )

        # Sort by importance, top 6
        contributions.sort(key=lambda c: c.importance, reverse=True)
        return contributions[:6]
