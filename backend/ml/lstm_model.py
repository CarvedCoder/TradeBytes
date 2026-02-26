"""
LSTM Model Architecture for Price Direction & Magnitude Prediction.

Multi-layer LSTM with attention mechanism and dual-head output:
- Direction head: binary classification (up/down)
- Magnitude head: regression (expected return)

Architecture:
  Input (batch, seq_len=60, features=24)
    → LayerNorm
    → LSTM (3 layers, hidden=128, dropout=0.3)
    → Self-Attention
    → Combined Loss Head:
        → Direction Head (Linear → Sigmoid) → P(up)
        → Magnitude Head (Linear → Tanh) → expected_return
"""

from __future__ import annotations

import math
from typing import NamedTuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class LSTMPrediction(NamedTuple):
    """Model output container."""
    direction_logit: torch.Tensor      # (batch,) raw logit for direction
    direction_prob: torch.Tensor       # (batch,) P(up)
    expected_return: torch.Tensor      # (batch,) predicted return magnitude
    confidence: torch.Tensor           # (batch,) prediction confidence
    attention_weights: torch.Tensor    # (batch, seq_len) attention weights


class TemporalAttention(nn.Module):
    """Scaled dot-product self-attention over time steps."""

    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.query = nn.Linear(hidden_size, hidden_size)
        self.key = nn.Linear(hidden_size, hidden_size)
        self.value = nn.Linear(hidden_size, hidden_size)
        self.scale = math.sqrt(hidden_size)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            x: (batch, seq_len, hidden_size)
        Returns:
            context: (batch, hidden_size) - attention-weighted representation
            weights: (batch, seq_len) - attention weights
        """
        Q = self.query(x)   # (batch, seq_len, hidden)
        K = self.key(x)     # (batch, seq_len, hidden)
        V = self.value(x)   # (batch, seq_len, hidden)

        # Attention scores
        scores = torch.bmm(Q, K.transpose(1, 2)) / self.scale  # (batch, seq_len, seq_len)
        weights = F.softmax(scores[:, -1, :], dim=-1)           # (batch, seq_len) - attend from last timestep
        context = torch.bmm(weights.unsqueeze(1), V).squeeze(1) # (batch, hidden)

        return context, weights


class StockLSTM(nn.Module):
    """
    Multi-layer LSTM for financial time-series prediction.
    
    Dual-head architecture:
    - Direction head: P(price goes up in next period)
    - Magnitude head: expected return percentage
    
    Args:
        input_size: Number of input features per timestep (default: 24)
        hidden_size: LSTM hidden state dimension (default: 128)
        num_layers: Number of stacked LSTM layers (default: 3)
        dropout: Dropout rate between LSTM layers (default: 0.3)
        use_attention: Whether to use temporal attention (default: True)
    """

    def __init__(
        self,
        input_size: int = 24,
        hidden_size: int = 128,
        num_layers: int = 3,
        dropout: float = 0.3,
        use_attention: bool = True,
    ) -> None:
        super().__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.use_attention = use_attention

        # Input normalization
        self.input_norm = nn.LayerNorm(input_size)

        # Core LSTM
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
            bidirectional=False,
        )

        # Attention mechanism
        if use_attention:
            self.attention = TemporalAttention(hidden_size)

        # Feature projection
        self.feature_proj = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, hidden_size // 2),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # Direction head (binary classification)
        self.direction_head = nn.Sequential(
            nn.Linear(hidden_size // 2, 32),
            nn.GELU(),
            nn.Linear(32, 1),
        )

        # Magnitude head (regression)
        self.magnitude_head = nn.Sequential(
            nn.Linear(hidden_size // 2, 32),
            nn.GELU(),
            nn.Linear(32, 1),
            nn.Tanh(),  # Bound output to [-1, 1]
        )

        # Confidence head
        self.confidence_head = nn.Sequential(
            nn.Linear(hidden_size // 2, 16),
            nn.GELU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

        self._init_weights()

    def _init_weights(self) -> None:
        """Xavier initialization for linear layers, orthogonal for LSTM."""
        for name, param in self.lstm.named_parameters():
            if "weight_ih" in name:
                nn.init.xavier_uniform_(param)
            elif "weight_hh" in name:
                nn.init.orthogonal_(param)
            elif "bias" in name:
                nn.init.zeros_(param)

        for module in [self.feature_proj, self.direction_head, self.magnitude_head, self.confidence_head]:
            for m in module.modules():
                if isinstance(m, nn.Linear):
                    nn.init.xavier_uniform_(m.weight)
                    if m.bias is not None:
                        nn.init.zeros_(m.bias)

    def forward(
        self,
        x: torch.Tensor,
        h0: torch.Tensor | None = None,
        c0: torch.Tensor | None = None,
    ) -> LSTMPrediction:
        """
        Forward pass.
        
        Args:
            x: (batch, seq_len, input_size) - feature sequence
            h0, c0: optional initial hidden/cell states
            
        Returns:
            LSTMPrediction with all output components
        """
        batch_size = x.size(0)

        # Normalize input
        x = self.input_norm(x)

        # Initialize hidden state if not provided
        if h0 is None or c0 is None:
            h0 = torch.zeros(self.num_layers, batch_size, self.hidden_size, device=x.device)
            c0 = torch.zeros(self.num_layers, batch_size, self.hidden_size, device=x.device)

        # LSTM forward
        lstm_out, (hn, cn) = self.lstm(x, (h0, c0))
        # lstm_out: (batch, seq_len, hidden_size)

        # Attention or last hidden state
        if self.use_attention:
            context, attn_weights = self.attention(lstm_out)
        else:
            context = lstm_out[:, -1, :]  # Last timestep
            attn_weights = torch.zeros(batch_size, x.size(1), device=x.device)

        # Feature projection
        features = self.feature_proj(context)

        # Dual heads
        direction_logit = self.direction_head(features).squeeze(-1)
        direction_prob = torch.sigmoid(direction_logit)
        expected_return = self.magnitude_head(features).squeeze(-1) * 0.1  # Scale to ±10%
        confidence = self.confidence_head(features).squeeze(-1)

        return LSTMPrediction(
            direction_logit=direction_logit,
            direction_prob=direction_prob,
            expected_return=expected_return,
            confidence=confidence,
            attention_weights=attn_weights,
        )


class CombinedLoss(nn.Module):
    """
    Combined loss for dual-head LSTM:
    L = α * BCE(direction) + β * MSE(magnitude) + γ * confidence_penalty
    
    The confidence penalty encourages the model to output high confidence
    when predictions are correct and low confidence when wrong.
    """

    def __init__(
        self,
        direction_weight: float = 0.6,
        magnitude_weight: float = 0.3,
        confidence_weight: float = 0.1,
    ) -> None:
        super().__init__()
        self.direction_weight = direction_weight
        self.magnitude_weight = magnitude_weight
        self.confidence_weight = confidence_weight
        self.bce = nn.BCEWithLogitsLoss()
        self.mse = nn.MSELoss()

    def forward(
        self,
        prediction: LSTMPrediction,
        direction_target: torch.Tensor,   # (batch,) binary: 1=up, 0=down
        return_target: torch.Tensor,      # (batch,) actual return
    ) -> tuple[torch.Tensor, dict[str, float]]:
        """
        Compute combined loss.
        
        Returns:
            total_loss: scalar tensor
            loss_components: dict of individual loss values
        """
        # Direction loss (BCE)
        direction_loss = self.bce(prediction.direction_logit, direction_target.float())

        # Magnitude loss (MSE)
        magnitude_loss = self.mse(prediction.expected_return, return_target)

        # Confidence calibration loss
        direction_correct = (prediction.direction_prob.round() == direction_target).float()
        confidence_loss = self.mse(prediction.confidence, direction_correct)

        total_loss = (
            self.direction_weight * direction_loss
            + self.magnitude_weight * magnitude_loss
            + self.confidence_weight * confidence_loss
        )

        components = {
            "direction_loss": direction_loss.item(),
            "magnitude_loss": magnitude_loss.item(),
            "confidence_loss": confidence_loss.item(),
            "total_loss": total_loss.item(),
        }

        return total_loss, components
