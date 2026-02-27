"""
Trading Endpoints - Execute simulated trades.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.trading import (
    TradeRequest,
    TradeResponse,
    TradeHistory,
)
from backend.services.trading_service import TradingService

router = APIRouter()


@router.post("/execute", response_model=TradeResponse)
async def execute_trade(
    trade: TradeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Execute a simulated trade.
    
    When a user trades, the system also:
    1. Updates portfolio positions
    2. Triggers AI competitor prediction
    3. Generates AI explanation
    4. Awards XP via gamification engine
    """
    service = TradingService(db)
    try:
        return await service.execute_trade(user_id, trade)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/history", response_model=list[TradeHistory])
async def get_trade_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    ticker: str | None = None,
    limit: int = 100,
    offset: int = 0,
):
    """Get user's trade history, optionally filtered by ticker."""
    service = TradingService(db)
    return await service.get_history(user_id, ticker=ticker, limit=limit, offset=offset)


@router.get("/history/{trade_id}", response_model=TradeHistory)
async def get_trade_detail(
    trade_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific trade including AI explanation."""
    service = TradingService(db)
    try:
        return await service.get_trade_detail(user_id, trade_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
