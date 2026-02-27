"""
Feature Engineering Pipeline.

Computes market features, sentiment features, and user context features.
Supports both batch (offline) and incremental (online) computation.

Feature categories:
1. Market features: RSI, MACD, Bollinger, volatility, trend indicators
2. Sentiment features: FinBERT scores, sentiment trends
3. User context features: portfolio state, trade patterns
4. Derived features: cross-feature interactions, lag features
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class FeatureConfig:
    """Configuration for feature computation."""
    sequence_length: int = 60
    market_features: list[str] | None = None
    sentiment_features: list[str] | None = None
    include_user_context: bool = False
    version: str = "v1.0"

    def __post_init__(self):
        if self.market_features is None:
            self.market_features = [
                "returns", "log_returns", "volatility_5", "volatility_20",
                "rsi_14", "macd", "macd_signal", "macd_histogram",
                "sma_20_dist", "sma_50_dist", "ema_12_dist", "ema_26_dist",
                "bollinger_upper_dist", "bollinger_lower_dist",
                "atr_14", "obv_norm", "volume_sma_ratio",
                "high_low_range", "open_close_range",
            ]
        if self.sentiment_features is None:
            self.sentiment_features = [
                "sentiment_score", "sentiment_momentum",
                "article_count_norm", "positive_ratio", "negative_ratio",
            ]

    @property
    def total_features(self) -> int:
        n = len(self.market_features or []) + len(self.sentiment_features or [])
        return n

    @property
    def schema_hash(self) -> str:
        features = sorted((self.market_features or []) + (self.sentiment_features or []))
        return hashlib.sha256("|".join(features).encode()).hexdigest()[:16]


class MarketFeatureGenerator:
    """Computes technical indicator features from OHLCV data."""

    def __init__(self, config: FeatureConfig) -> None:
        self.config = config

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute all market features from OHLCV DataFrame.
        
        Input columns: open, high, low, close, volume
        Output: DataFrame with all feature columns added.
        """
        df = df.copy()

        # Returns
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        # Volatility
        df["volatility_5"] = df["returns"].rolling(5).std()
        df["volatility_20"] = df["returns"].rolling(20).std()

        # RSI
        df["rsi_14"] = self._rsi(df["close"], 14)

        # MACD
        ema12 = df["close"].ewm(span=12).mean()
        ema26 = df["close"].ewm(span=26).mean()
        df["macd"] = ema12 - ema26
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

        # Moving averages (distance from price, normalized)
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["sma_20_dist"] = (df["close"] - df["sma_20"]) / df["sma_20"]
        df["sma_50_dist"] = (df["close"] - df["sma_50"]) / df["sma_50"]

        # EMA distances
        df["ema_12"] = ema12
        df["ema_26"] = ema26
        df["ema_12_dist"] = (df["close"] - ema12) / ema12
        df["ema_26_dist"] = (df["close"] - ema26) / ema26

        # Bollinger Bands
        bb_mid = df["close"].rolling(20).mean()
        bb_std = df["close"].rolling(20).std()
        df["bollinger_upper"] = bb_mid + 2 * bb_std
        df["bollinger_lower"] = bb_mid - 2 * bb_std
        df["bollinger_upper_dist"] = (df["close"] - df["bollinger_upper"]) / df["close"]
        df["bollinger_lower_dist"] = (df["close"] - df["bollinger_lower"]) / df["close"]

        # ATR
        df["atr_14"] = self._atr(df, 14)

        # OBV (normalized)
        df["obv"] = self._obv(df)
        df["obv_norm"] = (df["obv"] - df["obv"].rolling(20).mean()) / (df["obv"].rolling(20).std() + 1e-8)

        # Volume features
        df["volume_sma_ratio"] = df["volume"] / (df["volume"].rolling(20).mean() + 1e-8)

        # Range features
        df["high_low_range"] = (df["high"] - df["low"]) / df["close"]
        df["open_close_range"] = (df["close"] - df["open"]) / df["open"]

        return df

    @staticmethod
    def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        delta = prices.diff()
        gain = delta.where(delta > 0, 0).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / (loss + 1e-8)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()

    @staticmethod
    def _obv(df: pd.DataFrame) -> pd.Series:
        obv = [0]
        for i in range(1, len(df)):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                obv.append(obv[-1] + df["volume"].iloc[i])
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                obv.append(obv[-1] - df["volume"].iloc[i])
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=df.index)


class SentimentFeatureGenerator:
    """Computes sentiment features from news data."""

    def compute(self, sentiment_df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
        """Merge sentiment data with price data aligned by date.
        
        Input: sentiment_df with columns [date, sentiment_score, article_count, positive_ratio, negative_ratio]
        Output: DataFrame with sentiment features aligned to market dates.
        """
        if sentiment_df.empty:
            result = pd.DataFrame(index=price_df.index)
            result["sentiment_score"] = 0.0
            result["sentiment_momentum"] = 0.0
            result["article_count_norm"] = 0.0
            result["positive_ratio"] = 0.0
            result["negative_ratio"] = 0.0
            return result

        # Merge on date
        merged = price_df.merge(sentiment_df, left_index=True, right_index=True, how="left")
        merged["sentiment_score"] = merged["sentiment_score"].fillna(0).rolling(3).mean()
        merged["sentiment_momentum"] = merged["sentiment_score"].diff(5)
        merged["article_count_norm"] = merged["article_count"] / (merged["article_count"].rolling(20).mean() + 1e-8)

        return merged[["sentiment_score", "sentiment_momentum", "article_count_norm", "positive_ratio", "negative_ratio"]]


class FeatureBuilder:
    """Builds complete feature tensors for LSTM input.
    
    Applies per-feature z-score standardization to ensure all features
    have similar scale, which is critical for LSTM convergence.
    """

    def __init__(self, config: FeatureConfig | None = None) -> None:
        self.config = config or FeatureConfig()
        self.market_gen = MarketFeatureGenerator(self.config)
        self.sentiment_gen = SentimentFeatureGenerator()
        # Scaler statistics (fitted during build_tensor, reused for inference)
        self.feature_means_: np.ndarray | None = None
        self.feature_stds_: np.ndarray | None = None
        self.feature_names_: list[str] | None = None

    def build_tensor(
        self,
        ohlcv_df: pd.DataFrame,
        sentiment_df: pd.DataFrame | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Build feature tensors for LSTM training/inference.
        
        Returns:
            X: (num_samples, seq_len, num_features) - standardized input features
            y_direction: (num_samples,) - binary direction labels
            y_return: (num_samples,) - actual returns
        """
        # Compute market features
        featured_df = self.market_gen.compute(ohlcv_df)

        # Compute sentiment features (only include if real data provided)
        if sentiment_df is not None:
            sent_features = self.sentiment_gen.compute(sentiment_df, featured_df)
            featured_df = pd.concat([featured_df, sent_features], axis=1)
            feature_pool = (self.config.market_features or []) + (self.config.sentiment_features or [])
        else:
            # No sentiment data: only use market features (avoids dead zero columns)
            feature_pool = list(self.config.market_features or [])

        # Select feature columns that actually exist
        feature_cols = [c for c in feature_pool if c in featured_df.columns]

        # Drop NaN rows (from rolling computations)
        featured_df = featured_df.dropna(subset=feature_cols)

        # Build feature matrix and compute scaler stats
        feature_matrix = featured_df[feature_cols].values.astype(np.float32)
        close_prices = featured_df["close"].values

        # Per-feature z-score normalization (fit on full data before sequencing)
        self.feature_means_ = feature_matrix.mean(axis=0)
        self.feature_stds_ = feature_matrix.std(axis=0)
        self.feature_stds_[self.feature_stds_ < 1e-8] = 1.0  # avoid division by zero
        self.feature_names_ = feature_cols

        feature_matrix = (feature_matrix - self.feature_means_) / self.feature_stds_

        # Create sequences
        seq_len = self.config.sequence_length
        X_sequences = []
        y_directions = []
        y_returns = []

        for i in range(seq_len, len(feature_matrix) - 1):
            X_sequences.append(feature_matrix[i - seq_len:i])
            future_return = (close_prices[i + 1] - close_prices[i]) / close_prices[i]
            y_directions.append(1 if future_return > 0 else 0)
            y_returns.append(future_return)

        X = np.array(X_sequences, dtype=np.float32)
        y_dir = np.array(y_directions, dtype=np.float32)
        y_ret = np.array(y_returns, dtype=np.float32)

        return X, y_dir, y_ret

    def build_inference_tensor(
        self,
        ohlcv_df: pd.DataFrame,
        sentiment_df: pd.DataFrame | None = None,
        scaler: dict | None = None,
    ) -> np.ndarray:
        """Build a single feature tensor for inference (last seq_len candles).

        If `scaler` is provided (dict with 'means', 'stds', 'names'), uses those
        training-time statistics for normalization so the features match what the
        model was trained on.  Without a scaler the stats are re-fitted on the
        incoming data which causes train/inference skew.

        Returns: (1, seq_len, num_features)
        """
        if scaler and 'means' in scaler and 'stds' in scaler:
            return self._build_inference_with_scaler(ohlcv_df, sentiment_df, scaler)

        # Fallback: re-fit on incoming data (not recommended for production)
        X, _, _ = self.build_tensor(ohlcv_df, sentiment_df)
        if len(X) == 0:
            raise ValueError("Insufficient data to build feature tensor")
        return X[-1:].copy()  # Last sequence only

    def _build_inference_with_scaler(
        self,
        ohlcv_df: pd.DataFrame,
        sentiment_df: pd.DataFrame | None,
        scaler: dict,
    ) -> np.ndarray:
        """Build features using saved training-time normalization stats."""
        featured_df = self.market_gen.compute(ohlcv_df)

        if sentiment_df is not None:
            sent_features = self.sentiment_gen.compute(sentiment_df, featured_df)
            featured_df = pd.concat([featured_df, sent_features], axis=1)

        feature_names = list(scaler['names'])
        feature_cols = [c for c in feature_names if c in featured_df.columns]
        if len(feature_cols) != len(feature_names):
            missing = set(feature_names) - set(feature_cols)
            raise ValueError(f"Missing features in data: {missing}")

        featured_df = featured_df.dropna(subset=feature_cols)
        feature_matrix = featured_df[feature_cols].values.astype(np.float32)

        # Apply training-time normalization
        means = np.array(scaler['means'], dtype=np.float32)
        stds = np.array(scaler['stds'], dtype=np.float32)
        feature_matrix = (feature_matrix - means) / stds

        seq_len = self.config.sequence_length
        if len(feature_matrix) < seq_len:
            raise ValueError(
                f"Need at least {seq_len} candles after feature computation, got {len(feature_matrix)}"
            )

        # Take the last seq_len rows as the single inference sequence
        return feature_matrix[-seq_len:][np.newaxis, :, :]  # (1, seq_len, features)


class FeatureStore:
    """Online + offline feature store with versioning.
    
    Online: Redis (latest features for inference)
    Offline: S3/Parquet (historical features for training)
    """

    def __init__(self, config: FeatureConfig | None = None) -> None:
        self.config = config or FeatureConfig()

    async def get_online_features(self, ticker: str) -> np.ndarray:
        """Fetch latest features from Redis for real-time inference."""
        # TODO: implement Redis feature retrieval
        raise NotImplementedError

    async def store_online_features(self, ticker: str, features: np.ndarray) -> None:
        """Store computed features in Redis for low-latency serving."""
        # TODO: implement Redis feature storage
        pass

    async def get_offline_features(
        self, ticker: str, start_date: str, end_date: str
    ) -> np.ndarray:
        """Fetch historical features from offline store for training."""
        # TODO: implement S3/Parquet retrieval
        raise NotImplementedError

    async def store_offline_features(
        self, ticker: str, features: np.ndarray, version: str
    ) -> None:
        """Store features in offline store with versioning."""
        # TODO: implement S3/Parquet storage
        pass
