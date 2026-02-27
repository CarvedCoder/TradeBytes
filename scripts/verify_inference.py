"""Verify that inference uses checkpoint scaler correctly."""
import torch
import numpy as np
from backend.ml.lstm_model import StockLSTM
from backend.ml.features import FeatureBuilder, FeatureConfig
import yfinance as yf

# Load checkpoint
ckpt = torch.load("./models/AAPL_best.pt", map_location="cpu", weights_only=False)
scaler = ckpt.get("feature_scaler", {})
print("=== CHECKPOINT SCALER ===")
print(f"Keys: {list(scaler.keys())}")
names = list(scaler["names"])
print(f"Features ({len(names)}): {names}")
print(f"Means: {np.round(scaler['means'], 4)}")
print(f"Stds:  {np.round(scaler['stds'], 4)}")

# Build model
cfg = ckpt["config"]
model = StockLSTM(
    input_size=cfg.input_size, hidden_size=cfg.hidden_size,
    num_layers=cfg.num_layers, dropout=cfg.dropout, use_attention=cfg.use_attention,
)
model.load_state_dict(ckpt["model_state_dict"])
model.eval()

# Fetch data
df = yf.Ticker("AAPL").history(period="6mo", interval="1d")
df.columns = [c.lower() for c in df.columns]
builder = FeatureBuilder(FeatureConfig(sequence_length=60))

# WITH scaler (correct)
X_with = builder.build_inference_tensor(df, scaler=scaler)
print(f"\n=== WITH TRAINING SCALER ===")
print(f"Shape: {X_with.shape}")
print(f"Feature vals (last step, first 5): {np.round(X_with[0, -1, :5], 4)}")

# WITHOUT scaler (old broken behavior)
X_without = builder.build_inference_tensor(df)
print(f"\n=== WITHOUT SCALER (old broken way) ===")
print(f"Shape: {X_without.shape}")
print(f"Feature vals (last step, first 5): {np.round(X_without[0, -1, :5], 4)}")

print(f"\nMax abs difference between tensors: {np.abs(X_with - X_without).max():.4f}")

# Run model on both
with torch.no_grad():
    pred_correct = model(torch.FloatTensor(X_with))
    pred_wrong = model(torch.FloatTensor(X_without))
    print(f"\nCORRECT (with scaler): dir={pred_correct.direction_prob.item():.4f}, "
          f"ret={pred_correct.expected_return.item():.6f}, "
          f"conf={pred_correct.confidence.item():.4f}")
    print(f"WRONG   (no scaler):   dir={pred_wrong.direction_prob.item():.4f}, "
          f"ret={pred_wrong.expected_return.item():.6f}, "
          f"conf={pred_wrong.confidence.item():.4f}")
