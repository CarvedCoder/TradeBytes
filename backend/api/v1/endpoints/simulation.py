"""
Simulation Endpoints - Historical Replay Engine.

Controls the stock playground where historical OHLCV data is streamed
candle-by-candle over WebSocket while the user trades with fake capital.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.simulation import (
    SimulationCreateRequest,
    SimulationCreateResponse,
    SimulationState,
    SimulationControlRequest,
    SimulationTradeRequest,
    SimulationTradeResponse,
    SimulationResult,
    AvailableTickers,
)
from backend.services.simulation_service import SimulationService

router = APIRouter()


@router.get("/tickers", response_model=AvailableTickers)
async def list_available_tickers(
    db: AsyncSession = Depends(get_db),
):
    """List tickers available for simulation with date ranges."""
    service = SimulationService(db)
    return await service.get_available_tickers()


@router.post("/create", response_model=SimulationCreateResponse)
async def create_simulation(
    request: SimulationCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new simulation session.
    
    Prepares historical data for streaming and initializes:
    - User's virtual capital
    - AI competitor state
    - Candle replay queue
    
    Returns session_id for WebSocket connection.
    """
    service = SimulationService(db)
    return await service.create_session(user_id, request)


@router.get("/{session_id}/state", response_model=SimulationState)
async def get_simulation_state(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current simulation state (positions, PnL, candle index)."""
    service = SimulationService(db)
    return await service.get_state(user_id, session_id)


@router.post("/{session_id}/control")
async def control_simulation(
    session_id: str,
    request: SimulationControlRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Control simulation playback: play, pause, speed change, skip."""
    service = SimulationService(db)
    return await service.control(user_id, session_id, request)


@router.post("/{session_id}/trade", response_model=SimulationTradeResponse)
async def simulation_trade(
    session_id: str,
    request: SimulationTradeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Execute a trade within a simulation session.
    
    Trades at the current candle's price. AI competitor also decides
    whether to trade and results are compared.
    """
    service = SimulationService(db)
    return await service.execute_trade(user_id, session_id, request)


@router.get("/{session_id}/result", response_model=SimulationResult)
async def get_simulation_result(
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get final simulation results after session completion."""
    service = SimulationService(db)
    return await service.get_result(user_id, session_id)
