"""Diagnostic: verify training pipeline correctness."""
import numpy as np
import pandas as pd
import torch

# 1. Check feature count mismatch
from backend.ml.features import FeatureBuilder, FeatureConfig
import yfinance as yf

df = yf.Ticker('AAPL').history(start='2020-01-01', end='2023-01-01', interval='1d')
df.columns = [c.lower() for c in df.columns]

cfg = FeatureConfig(sequence_length=60)
builder = FeatureBuilder(cfg)
X, y_dir, y_ret = builder.build_tensor(df)

print(f"=== DIAGNOSTIC REPORT ===")
print(f"\n1. FEATURE COUNT")
print(f"   FeatureConfig.total_features: {cfg.total_features}")
print(f"   Actual X.shape[2] (features in tensor): {X.shape[2]}")
print(f"   MATCH: {cfg.total_features == X.shape[2]}")

# 2. Check for NaN/Inf in features
print(f"\n2. DATA QUALITY")
print(f"   X has NaN: {np.isnan(X).any()}")
print(f"   X has Inf: {np.isinf(X).any()}")
print(f"   X range: [{X.min():.4f}, {X.max():.4f}]")
print(f"   y_dir unique values: {np.unique(y_dir)}")
print(f"   y_ret range: [{y_ret.min():.6f}, {y_ret.max():.6f}]")

# Check individual feature stats
for i in range(X.shape[2]):
    col = X[:, -1, i]  # last timestep across samples
    if np.isnan(col).any() or np.isinf(col).any():
        print(f"   WARNING: Feature {i} has NaN/Inf!")
    if np.std(col) < 1e-10:
        print(f"   WARNING: Feature {i} has near-zero variance (std={np.std(col):.2e})")

# 3. Check feature normalization
print(f"\n3. FEATURE SCALE (last timestep, per feature)")
for i in range(X.shape[2]):
    col = X[:, -1, i]
    print(f"   Feature {i:2d}: mean={np.mean(col):+.4f}, std={np.std(col):.4f}, "
          f"min={np.min(col):.4f}, max={np.max(col):.4f}")

# 4. Test model forward pass
print(f"\n4. MODEL FORWARD PASS")
from backend.ml.lstm_model import StockLSTM, CombinedLoss
model = StockLSTM(input_size=X.shape[2], hidden_size=128, num_layers=3)
model.eval()

sample = torch.FloatTensor(X[:5])
with torch.no_grad():
    pred = model(sample)
    print(f"   direction_prob: {pred.direction_prob.tolist()}")
    print(f"   expected_return: {pred.expected_return.tolist()}")
    print(f"   confidence: {pred.confidence.tolist()}")
    print(f"   attention sum: {pred.attention_weights.sum(dim=1).tolist()}")

# 5. Check loss computation
print(f"\n5. LOSS COMPUTATION")
criterion = CombinedLoss()
y_d = torch.FloatTensor(y_dir[:5])
y_r = torch.FloatTensor(y_ret[:5])
loss, comps = criterion(pred, y_d, y_r)
print(f"   total_loss: {comps['total_loss']:.6f}")
print(f"   direction_loss: {comps['direction_loss']:.6f}")
print(f"   magnitude_loss: {comps['magnitude_loss']:.6f}")
print(f"   confidence_loss: {comps['confidence_loss']:.6f}")

# 6. Check gradient flow
print(f"\n6. GRADIENT FLOW")
model.train()
pred = model(sample)
loss, _ = criterion(pred, y_d, y_r)
loss.backward()
grad_norms = {}
for name, p in model.named_parameters():
    if p.grad is not None:
        grad_norms[name] = p.grad.norm().item()
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
zero_grad_params = sum(1 for n, p in model.named_parameters() if p.grad is not None and p.grad.norm().item() < 1e-10)
print(f"   Total params: {total_params:,}")
print(f"   Trainable params: {trainable_params:,}")
print(f"   Params with zero gradient: {zero_grad_params}")
print(f"   Gradient norm range: [{min(grad_norms.values()):.6f}, {max(grad_norms.values()):.6f}]")

# 7. Check training dynamics (5 mini-epochs)
print(f"\n7. TRAINING DYNAMICS (5 steps)")
from torch.utils.data import DataLoader, TensorDataset
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
ds = TensorDataset(torch.FloatTensor(X[:200]), torch.FloatTensor(y_dir[:200]), torch.FloatTensor(y_ret[:200]))
loader = DataLoader(ds, batch_size=64, shuffle=False)

for step in range(5):
    model.train()
    epoch_loss = 0
    n = 0
    for xb, ydb, yrb in loader:
        optimizer.zero_grad()
        p = model(xb)
        l, c = criterion(p, ydb, yrb)
        l.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        epoch_loss += c['total_loss']
        n += 1
    print(f"   Step {step+1}: loss={epoch_loss/n:.6f}, "
          f"dir_loss={c['direction_loss']:.6f}, "
          f"mag_loss={c['magnitude_loss']:.6f}")

print(f"\n=== END DIAGNOSTIC ===")
