"""
Training Pipeline for LSTM Model.

End-to-end training with:
- Time-based train/val/test split (no data leakage)
- MLflow experiment tracking
- Model evaluation with backtesting
- Drift detection
- Model registry management
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import structlog
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from backend.ml.lstm_model import StockLSTM, CombinedLoss, LSTMPrediction

logger = structlog.get_logger()


@dataclass
class TrainingConfig:
    """Training hyperparameters and configuration."""
    # Model architecture
    input_size: int = 24
    hidden_size: int = 128
    num_layers: int = 3
    dropout: float = 0.3
    use_attention: bool = True

    # Training
    epochs: int = 100
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    lr_scheduler: str = "cosine"  # "cosine", "step", "plateau"
    early_stopping_patience: int = 15
    gradient_clip_norm: float = 1.0

    # Loss weights
    direction_weight: float = 0.6
    magnitude_weight: float = 0.3
    confidence_weight: float = 0.1

    # Data split (time-based)
    train_ratio: float = 0.7
    val_ratio: float = 0.15
    test_ratio: float = 0.15

    # MLflow
    experiment_name: str = "tradebytes-lstm"
    run_name: str | None = None

    # Paths
    model_save_dir: str = "./models"
    ticker: str = "AAPL"


@dataclass
class TrainingResult:
    """Training run results."""
    model_path: str = ""
    best_epoch: int = 0
    best_val_loss: float = float("inf")
    test_metrics: dict[str, float] = field(default_factory=dict)
    training_history: list[dict[str, float]] = field(default_factory=list)
    mlflow_run_id: str | None = None


class TimeSeriesDataset:
    """Handles time-based splitting with no data leakage."""

    def __init__(self, X: np.ndarray, y_dir: np.ndarray, y_ret: np.ndarray, config: TrainingConfig):
        self.X = X
        self.y_dir = y_dir
        self.y_ret = y_ret
        self.config = config

    def split(self) -> tuple[TensorDataset, TensorDataset, TensorDataset]:
        """Time-based train/val/test split.
        
        CRITICAL: No shuffling! Data must remain in chronological order
        to prevent look-ahead bias (data leakage).
        """
        n = len(self.X)
        train_end = int(n * self.config.train_ratio)
        val_end = int(n * (self.config.train_ratio + self.config.val_ratio))

        def to_dataset(start: int, end: int) -> TensorDataset:
            return TensorDataset(
                torch.FloatTensor(self.X[start:end]),
                torch.FloatTensor(self.y_dir[start:end]),
                torch.FloatTensor(self.y_ret[start:end]),
            )

        train_ds = to_dataset(0, train_end)
        val_ds = to_dataset(train_end, val_end)
        test_ds = to_dataset(val_end, n)

        logger.info(
            "Data split",
            train=len(train_ds), val=len(val_ds), test=len(test_ds),
            total=n,
        )

        return train_ds, val_ds, test_ds


class Trainer:
    """Handles the full training loop with MLflow tracking."""

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model: StockLSTM | None = None
        self.optimizer: torch.optim.Optimizer | None = None
        self.scheduler: Any = None
        self.criterion: CombinedLoss | None = None

    def train(self, X: np.ndarray, y_dir: np.ndarray, y_ret: np.ndarray) -> TrainingResult:
        """Full training pipeline."""
        result = TrainingResult()

        # 1. Split data (time-based)
        dataset = TimeSeriesDataset(X, y_dir, y_ret, self.config)
        train_ds, val_ds, test_ds = dataset.split()

        train_loader = DataLoader(train_ds, batch_size=self.config.batch_size, shuffle=False)
        val_loader = DataLoader(val_ds, batch_size=self.config.batch_size, shuffle=False)
        test_loader = DataLoader(test_ds, batch_size=self.config.batch_size, shuffle=False)

        # 2. Initialize model
        self.model = StockLSTM(
            input_size=self.config.input_size,
            hidden_size=self.config.hidden_size,
            num_layers=self.config.num_layers,
            dropout=self.config.dropout,
            use_attention=self.config.use_attention,
        ).to(self.device)

        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )

        self.criterion = CombinedLoss(
            direction_weight=self.config.direction_weight,
            magnitude_weight=self.config.magnitude_weight,
            confidence_weight=self.config.confidence_weight,
        )

        # Learning rate scheduler
        if self.config.lr_scheduler == "cosine":
            self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
                self.optimizer, T_max=self.config.epochs
            )
        elif self.config.lr_scheduler == "plateau":
            self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
                self.optimizer, patience=5, factor=0.5
            )

        # 3. Training loop
        best_val_loss = float("inf")
        patience_counter = 0

        for epoch in range(self.config.epochs):
            # Train
            train_metrics = self._train_epoch(train_loader)

            # Validate
            val_metrics = self._evaluate(val_loader)

            # Log
            logger.info(
                f"Epoch {epoch+1}/{self.config.epochs}",
                train_loss=f"{train_metrics['total_loss']:.4f}",
                val_loss=f"{val_metrics['total_loss']:.4f}",
                val_dir_acc=f"{val_metrics.get('direction_accuracy', 0):.4f}",
            )

            result.training_history.append({
                "epoch": epoch + 1,
                **{f"train_{k}": v for k, v in train_metrics.items()},
                **{f"val_{k}": v for k, v in val_metrics.items()},
            })

            # Scheduler step
            if isinstance(self.scheduler, torch.optim.lr_scheduler.ReduceLROnPlateau):
                self.scheduler.step(val_metrics["total_loss"])
            elif self.scheduler:
                self.scheduler.step()

            # Early stopping
            if val_metrics["total_loss"] < best_val_loss:
                best_val_loss = val_metrics["total_loss"]
                patience_counter = 0
                result.best_epoch = epoch + 1
                result.best_val_loss = best_val_loss
                self._save_checkpoint(epoch + 1, val_metrics)
            else:
                patience_counter += 1
                if patience_counter >= self.config.early_stopping_patience:
                    logger.info(f"Early stopping at epoch {epoch+1}")
                    break

        # 4. Evaluate on test set
        self._load_best_checkpoint()
        result.test_metrics = self._evaluate(test_loader)
        logger.info("Test metrics", **result.test_metrics)

        # 5. Save final model
        model_path = self._save_model()
        result.model_path = model_path

        return result

    def _train_epoch(self, loader: DataLoader) -> dict[str, float]:
        """Single training epoch."""
        assert self.model is not None and self.criterion is not None
        self.model.train()
        total_loss = 0.0
        all_components: dict[str, float] = {}
        n_batches = 0

        for X_batch, y_dir_batch, y_ret_batch in loader:
            X_batch = X_batch.to(self.device)
            y_dir_batch = y_dir_batch.to(self.device)
            y_ret_batch = y_ret_batch.to(self.device)

            self.optimizer.zero_grad()
            prediction = self.model(X_batch)
            loss, components = self.criterion(prediction, y_dir_batch, y_ret_batch)

            loss.backward()
            nn.utils.clip_grad_norm_(self.model.parameters(), self.config.gradient_clip_norm)
            self.optimizer.step()

            total_loss += loss.item()
            for k, v in components.items():
                all_components[k] = all_components.get(k, 0) + v
            n_batches += 1

        return {k: v / max(n_batches, 1) for k, v in all_components.items()}

    @torch.no_grad()
    def _evaluate(self, loader: DataLoader) -> dict[str, float]:
        """Evaluate model on a dataset."""
        assert self.model is not None and self.criterion is not None
        self.model.eval()
        all_components: dict[str, float] = {}
        all_preds = []
        all_targets = []
        n_batches = 0

        for X_batch, y_dir_batch, y_ret_batch in loader:
            X_batch = X_batch.to(self.device)
            y_dir_batch = y_dir_batch.to(self.device)
            y_ret_batch = y_ret_batch.to(self.device)

            prediction = self.model(X_batch)
            _, components = self.criterion(prediction, y_dir_batch, y_ret_batch)

            for k, v in components.items():
                all_components[k] = all_components.get(k, 0) + v

            all_preds.append(prediction.direction_prob.cpu().numpy())
            all_targets.append(y_dir_batch.cpu().numpy())
            n_batches += 1

        metrics = {k: v / max(n_batches, 1) for k, v in all_components.items()}

        # Direction accuracy
        if all_preds:
            preds = np.concatenate(all_preds)
            targets = np.concatenate(all_targets)
            metrics["direction_accuracy"] = float(np.mean((preds > 0.5) == targets))

        return metrics

    def _save_checkpoint(self, epoch: int, metrics: dict) -> None:
        """Save model checkpoint."""
        assert self.model is not None
        os.makedirs(self.config.model_save_dir, exist_ok=True)
        path = os.path.join(self.config.model_save_dir, f"{self.config.ticker}_best.pt")
        torch.save({
            "epoch": epoch,
            "model_state_dict": self.model.state_dict(),
            "optimizer_state_dict": self.optimizer.state_dict() if self.optimizer else None,
            "metrics": metrics,
            "config": self.config,
        }, path)

    def _load_best_checkpoint(self) -> None:
        """Load best checkpoint for evaluation."""
        assert self.model is not None
        path = os.path.join(self.config.model_save_dir, f"{self.config.ticker}_best.pt")
        if os.path.exists(path):
            checkpoint = torch.load(path, map_location=self.device)
            self.model.load_state_dict(checkpoint["model_state_dict"])

    def _save_model(self) -> str:
        """Save final model for deployment."""
        assert self.model is not None
        os.makedirs(self.config.model_save_dir, exist_ok=True)
        path = os.path.join(
            self.config.model_save_dir,
            f"{self.config.ticker}_lstm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        )
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "config": self.config,
            "timestamp": datetime.now().isoformat(),
        }, path)
        logger.info("Model saved", path=path)
        return path


class BacktestEngine:
    """Backtesting evaluation for trained models."""

    def __init__(self, model: StockLSTM, device: torch.device) -> None:
        self.model = model
        self.device = device

    @torch.no_grad()
    def backtest(
        self,
        X_test: np.ndarray,
        prices: np.ndarray,
        initial_capital: float = 10000.0,
    ) -> dict[str, Any]:
        """Run backtest simulation using model predictions.
        
        Returns performance metrics: returns, Sharpe, max drawdown, etc.
        """
        self.model.eval()
        capital = initial_capital
        position = 0.0
        trades = []
        portfolio_values = [capital]

        X_tensor = torch.FloatTensor(X_test).to(self.device)

        for i in range(len(X_test)):
            pred = self.model(X_tensor[i:i+1])
            direction_prob = pred.direction_prob.item()
            confidence = pred.confidence.item()

            price = float(prices[i])
            next_price = float(prices[i + 1]) if i + 1 < len(prices) else price

            # Simple strategy: buy if confident bullish, sell if confident bearish
            if direction_prob > 0.6 and confidence > 0.5 and position == 0:
                shares = capital / price
                position = shares
                capital = 0
                trades.append({"type": "buy", "price": price, "shares": shares})
            elif direction_prob < 0.4 and confidence > 0.5 and position > 0:
                capital = position * price
                trades.append({"type": "sell", "price": price, "shares": position})
                position = 0

            portfolio_value = capital + position * next_price
            portfolio_values.append(portfolio_value)

        # Metrics
        portfolio_values = np.array(portfolio_values)
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        total_return = (portfolio_values[-1] - initial_capital) / initial_capital

        sharpe = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252)
        max_drawdown = np.min(portfolio_values / np.maximum.accumulate(portfolio_values) - 1)

        return {
            "total_return": float(total_return),
            "sharpe_ratio": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "num_trades": len(trades),
            "final_value": float(portfolio_values[-1]),
            "win_rate": sum(1 for t in trades if t.get("pnl", 0) > 0) / max(len(trades), 1),
        }


class DriftDetector:
    """Detects data and concept drift for retraining triggers."""

    def __init__(self, reference_stats: dict | None = None) -> None:
        self.reference_stats = reference_stats or {}

    def compute_stats(self, features: np.ndarray) -> dict[str, float]:
        """Compute distribution statistics for a feature set."""
        return {
            "mean": float(np.mean(features)),
            "std": float(np.std(features)),
            "skew": float(self._skew(features)),
            "kurtosis": float(self._kurtosis(features)),
            "min": float(np.min(features)),
            "max": float(np.max(features)),
        }

    def detect_drift(
        self, current_features: np.ndarray, threshold: float = 2.0
    ) -> tuple[bool, dict]:
        """Detect if current features have drifted from reference distribution."""
        if not self.reference_stats:
            return False, {}

        current_stats = self.compute_stats(current_features)
        drift_scores = {}

        for key in ["mean", "std"]:
            ref_val = self.reference_stats.get(key, 0)
            cur_val = current_stats.get(key, 0)
            ref_std = self.reference_stats.get("std", 1)
            z_score = abs(cur_val - ref_val) / (ref_std + 1e-8)
            drift_scores[f"{key}_z_score"] = z_score

        max_drift = max(drift_scores.values()) if drift_scores else 0
        is_drifted = max_drift > threshold

        return is_drifted, {
            "max_drift_score": max_drift,
            "details": drift_scores,
            "threshold": threshold,
        }

    @staticmethod
    def _skew(x: np.ndarray) -> float:
        m = np.mean(x)
        s = np.std(x) + 1e-8
        return float(np.mean(((x - m) / s) ** 3))

    @staticmethod
    def _kurtosis(x: np.ndarray) -> float:
        m = np.mean(x)
        s = np.std(x) + 1e-8
        return float(np.mean(((x - m) / s) ** 4) - 3)
