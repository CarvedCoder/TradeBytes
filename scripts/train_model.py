"""
Train the LSTM model for stock price prediction.

Usage:
    python scripts/train_model.py                    # Train AAPL with defaults
    python scripts/train_model.py --ticker MSFT      # Train a different ticker
    python scripts/train_model.py --epochs 10        # Quick smoke test
"""

import argparse
import sys
import time

import numpy as np
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Train LSTM stock prediction model")
    parser.add_argument("--ticker", default="AAPL", help="Stock ticker (default: AAPL)")
    parser.add_argument("--start", default="2018-01-01", help="Start date (default: 2018-01-01)")
    parser.add_argument("--end", default="2025-12-31", help="End date (default: 2025-12-31)")
    parser.add_argument("--epochs", type=int, default=50, help="Max training epochs (default: 50)")
    parser.add_argument("--batch-size", type=int, default=64, help="Batch size (default: 64)")
    parser.add_argument("--hidden-size", type=int, default=128, help="LSTM hidden size (default: 128)")
    parser.add_argument("--num-layers", type=int, default=3, help="LSTM layers (default: 3)")
    parser.add_argument("--seq-length", type=int, default=60, help="Sequence length (default: 60)")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate (default: 3e-4)")
    parser.add_argument("--warmup", type=int, default=5, help="LR warmup epochs (default: 5)")
    parser.add_argument("--patience", type=int, default=15, help="Early stopping patience (default: 15)")
    parser.add_argument("--model-dir", default="./models", help="Model save directory (default: ./models)")
    parser.add_argument("--backtest", action="store_true", help="Run backtest after training")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  TradeBytes LSTM Training Pipeline")
    print(f"  Ticker: {args.ticker}")
    print(f"  Date range: {args.start} to {args.end}")
    print(f"  Epochs: {args.epochs}, Batch: {args.batch_size}")
    print("=" * 60)

    # ── Step 1: Fetch data ──────────────────────────────────────
    print("\n[1/4] Fetching historical data via yfinance...")
    try:
        import yfinance as yf
    except ImportError:
        print("ERROR: yfinance not installed. Run: pip install yfinance")
        sys.exit(1)

    df = yf.Ticker(args.ticker).history(start=args.start, end=args.end, interval="1d")
    if df.empty:
        print(f"ERROR: No data returned for {args.ticker} in range {args.start} to {args.end}")
        sys.exit(1)

    df.columns = [c.lower() for c in df.columns]
    print(f"  ✓ {len(df)} daily candles fetched ({df.index[0].date()} → {df.index[-1].date()})")

    # ── Step 2: Build features ──────────────────────────────────
    print("\n[2/4] Engineering features...")
    from backend.ml.features import FeatureBuilder, FeatureConfig

    feat_config = FeatureConfig(sequence_length=args.seq_length)
    builder = FeatureBuilder(feat_config)
    X, y_dir, y_ret = builder.build_tensor(df)
    actual_features = X.shape[2]
    print(f"  ✓ X shape: {X.shape}  (samples, seq_len, features)")
    print(f"    Features used: {builder.feature_names_}")
    print(f"    y_direction: {y_dir.shape}  ({y_dir.sum():.0f} up / {len(y_dir) - y_dir.sum():.0f} down)")
    print(f"    y_return: mean={y_ret.mean():.5f}, std={y_ret.std():.5f}")

    # Verify features are standardized
    sample_means = X[:, -1, :].mean(axis=0)
    sample_stds = X[:, -1, :].std(axis=0)
    print(f"    Feature means (should be ~0): [{sample_means.min():.3f}, {sample_means.max():.3f}]")
    print(f"    Feature stds  (should be ~1): [{sample_stds.min():.3f}, {sample_stds.max():.3f}]")

    # ── Step 3: Train ───────────────────────────────────────────
    print("\n[3/4] Training model...")
    import torch
    from backend.ml.training import Trainer, TrainingConfig

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Device: {device}")
    if device == "cuda":
        print(f"  GPU: {torch.cuda.get_device_name(0)}")

    train_config = TrainingConfig(
        input_size=actual_features,  # Use actual feature count from tensor
        hidden_size=args.hidden_size,
        num_layers=args.num_layers,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        warmup_epochs=args.warmup,
        early_stopping_patience=args.patience,
        ticker=args.ticker,
        model_save_dir=args.model_dir,
    )

    trainer = Trainer(train_config)
    t0 = time.time()

    # Pass feature scaler stats so they get saved in the checkpoint
    feature_scaler = {
        'means': builder.feature_means_,
        'stds': builder.feature_stds_,
        'names': builder.feature_names_,
    }
    result = trainer.train(X, y_dir, y_ret, feature_scaler=feature_scaler)
    elapsed = time.time() - t0

    print(f"\n  ✓ Training complete in {elapsed:.1f}s")
    print(f"    Best epoch: {result.best_epoch}")
    print(f"    Best val loss: {result.best_val_loss:.4f}")
    print(f"    Test direction accuracy: {result.test_metrics.get('direction_accuracy', 0):.4f}")
    print(f"    Model saved: {result.model_path}")

    # ── Step 4: Optional backtest ───────────────────────────────
    if args.backtest:
        print("\n[4/4] Running backtest...")
        from backend.ml.training import BacktestEngine
        from backend.ml.lstm_model import StockLSTM

        # Load the best model
        checkpoint = torch.load(
            f"{args.model_dir}/{args.ticker}_best.pt",
            map_location=torch.device(device),
            weights_only=False,
        )
        model = StockLSTM(
            input_size=train_config.input_size,
            hidden_size=train_config.hidden_size,
            num_layers=train_config.num_layers,
            dropout=train_config.dropout,
            use_attention=train_config.use_attention,
        )
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(torch.device(device))

        # Use test split for backtest
        test_start = int(len(X) * (train_config.train_ratio + train_config.val_ratio))
        X_test = X[test_start:]

        # Align prices: each sample i in X corresponds to predicting the candle
        # at offset (seq_length + i) in the NaN-dropped featured DataFrame.
        # We need prices[i] and prices[i+1] for each test sample.
        # The featured df after dropna starts at ~row 50 of original df.
        # After sequencing, sample j uses candles [j, j+seq_len) and predicts
        # candle j+seq_len → j+seq_len+1. So price at sample j = close[j+seq_len].
        # For the test split starting at test_start, prices start at
        # close[test_start + seq_len] in the featured df.
        all_close = df["close"].dropna().values
        # The feature pipeline drops ~50 rows for rolling warmup, then creates
        # len(featured)-seq_len-1 samples. We need raw close prices aligned.
        # Simplest: refetch from the original df using the feature builder's
        # computed offsets. The close prices corresponding to X[i] prediction
        # target are at positions (offset + seq_len + i) and (offset + seq_len + i + 1)
        # in the original close array.
        # Since build_tensor drops NaN rows first, let's compute the offset:
        featured_df_tmp = builder.market_gen.compute(df)
        market_cols = [c for c in (builder.config.market_features or []) if c in featured_df_tmp.columns]
        featured_df_tmp = featured_df_tmp.dropna(subset=market_cols)
        close_after_dropna = featured_df_tmp["close"].values
        # For sample i: target = close[seq_len + i + 1], current = close[seq_len + i]
        # Test samples start at test_start
        seq_len = feat_config.sequence_length
        price_start = seq_len + test_start
        price_end = seq_len + test_start + len(X_test) + 1
        if price_end > len(close_after_dropna):
            price_end = len(close_after_dropna)
        prices_aligned = close_after_dropna[price_start:price_end]

        print(f"  X_test: {X_test.shape}, prices: {prices_aligned.shape}")

        engine = BacktestEngine(model, torch.device(device))
        bt = engine.backtest(X_test, prices_aligned, initial_capital=10000.0)

        print(f"  ✓ Backtest results:")
        print(f"    Total return: {bt['total_return']:.2%}")
        print(f"    Sharpe ratio: {bt['sharpe_ratio']:.2f}")
        print(f"    Max drawdown: {bt['max_drawdown']:.2%}")
        print(f"    Num trades: {bt['num_trades']}")
        print(f"    Final value: ${bt['final_value']:,.2f}")
    else:
        print("\n[4/4] Skipping backtest (use --backtest to enable)")

    print("\n" + "=" * 60)
    print("  Done! Model ready for inference.")
    print("=" * 60)


if __name__ == "__main__":
    main()
