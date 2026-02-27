import asyncio
import pandas as pd
from backend.ml.features import FeatureBuilder, FeatureConfig
from backend.ml.training import Trainer, TrainingConfig

async def train():
    # 1. Fetch OHLCV data via yfinance
    import yfinance as yf
    ticker = "AAPL"
    df = yf.Ticker(ticker).history(start="2018-01-01", end="2025-12-31", interval="1d")
    df.columns = [c.lower() for c in df.columns]  # lowercase for feature pipeline
    print(f"Fetched {len(df)} candles for {ticker}")

    # 2. Build feature tensors
    config = FeatureConfig(sequence_length=60)
    builder = FeatureBuilder(config)
    X, y_dir, y_ret = builder.build_tensor(df)
    print(f"Feature tensor: X={X.shape}, y_dir={y_dir.shape}, y_ret={y_ret.shape}")

    # 3. Train
    train_config = TrainingConfig(
        input_size=config.total_features,  # 24 features
        ticker=ticker,
        epochs=50,              # reduce for quick test
        batch_size=64,
        hidden_size=128,
        num_layers=3,
        early_stopping_patience=10,
        model_save_dir="./models",
    )
    trainer = Trainer(train_config)
    result = trainer.train(X, y_dir, y_ret)

    print(f"\nTraining complete!")
    print(f"  Best epoch: {result.best_epoch}")
    print(f"  Best val loss: {result.best_val_loss:.4f}")
    print(f"  Test direction accuracy: {result.test_metrics.get('direction_accuracy', 0):.4f}")
    print(f"  Model saved to: {result.model_path}")

asyncio.run(train())