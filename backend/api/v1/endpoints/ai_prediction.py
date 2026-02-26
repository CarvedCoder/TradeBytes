"""
AI Prediction Endpoints - LSTM Predictions & Explanations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    PredictionExplanation,
    ModelPerformanceResponse,
)
from backend.services.prediction_service import PredictionService

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
async def get_prediction(
    request: PredictionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get LSTM price prediction for a ticker.
    
    Returns:
    - Direction probability (up/down)
    - Expected return magnitude
    - Confidence score
    - Contributing features
    """
    service = PredictionService(db)
    return await service.predict(request)


@router.get("/explain/{trade_id}", response_model=PredictionExplanation)
async def get_prediction_explanation(
    trade_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get AI explanation for why a prediction was made."""
    service = PredictionService(db)
    return await service.explain(trade_id)


@router.get("/performance", response_model=ModelPerformanceResponse)
async def get_model_performance(
    db: AsyncSession = Depends(get_db),
    ticker: str | None = None,
):
    """Get model performance metrics (accuracy, returns, etc.)."""
    service = PredictionService(db)
    return await service.get_performance(ticker)
