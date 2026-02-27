"""Quick inference test for trained LSTM model."""
import torch
import numpy as np
from backend.ml.lstm_model import StockLSTM
from backend.ml.features import FeatureBuilder, FeatureConfig
import yfinance as yf

# Load the trained model
ckpt = torch.load('./models/AAPL_best.pt', map_location='cpu', weights_only=False)
cfg = ckpt['config']
model = StockLSTM(
    input_size=cfg.input_size, hidden_size=cfg.hidden_size,
    num_layers=cfg.num_layers, dropout=cfg.dropout, use_attention=cfg.use_attention,
)
model.load_state_dict(ckpt['model_state_dict'])
model.eval()
print("Model loaded OK")

# Load feature scaler from checkpoint
scaler = ckpt.get('feature_scaler', {})
if scaler:
    print(f"Feature scaler loaded: {len(scaler['names'])} features")
else:
    print("WARNING: No feature scaler in checkpoint, normalization may be wrong")

# Build features from live data
df = yf.Ticker('AAPL').history(period='6mo', interval='1d')
df.columns = [c.lower() for c in df.columns]
builder = FeatureBuilder(FeatureConfig(sequence_length=60))
X = builder.build_inference_tensor(df, scaler=scaler)
print(f"Features: {X.shape}")

# Run inference
with torch.no_grad():
    pred = model(torch.FloatTensor(X))
    prob = pred.direction_prob.item()
    direction = "UP" if prob > 0.5 else "DOWN"
    print(f"\n=== AAPL Prediction ===")
    print(f"Direction:      {direction}")
    print(f"Direction prob: {prob:.4f}")
    print(f"Expected return:{pred.expected_return.item():.6f}")
    print(f"Confidence:     {pred.confidence.item():.4f}")

    # Current price
    price = yf.Ticker('AAPL').fast_info.last_price
    predicted_price = price * (1 + pred.expected_return.item())
    print(f"Current price:  ${price:.2f}")
    print(f"Predicted price:${predicted_price:.2f}")
