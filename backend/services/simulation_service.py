"""
Simulation Service - Historical Replay Engine.

Manages stock playground sessions where historical OHLCV data is streamed
candle-by-candle while users trade with fake capital.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.models.trading import SimulationSession, OHLCVCandle, Trade
from backend.schemas.simulation import (
    SimulationCreateRequest,
    SimulationCreateResponse,
    SimulationState,
    SimulationControlRequest,
    SimulationTradeRequest,
    SimulationTradeResponse,
    SimulationResult,
    AvailableTickers,
    TickerInfo,
)

logger = structlog.get_logger()
settings = get_settings()


class SimulationService:
    """Controls the historical replay engine and simulation sessions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_available_tickers(self) -> AvailableTickers:
        """List tickers with available historical data."""
        # Query distinct tickers from OHLCV data with date ranges
        # In production: query TimescaleDB
        tickers = [
            TickerInfo(
                ticker="AAPL", name="Apple Inc.", sector="Technology",
                earliest_date="2015-01-02", latest_date="2025-12-31", total_candles=2768,
            ),
            TickerInfo(
                ticker="GOOGL", name="Alphabet Inc.", sector="Technology",
                earliest_date="2015-01-02", latest_date="2025-12-31", total_candles=2768,
            ),
            TickerInfo(
                ticker="MSFT", name="Microsoft Corporation", sector="Technology",
                earliest_date="2015-01-02", latest_date="2025-12-31", total_candles=2768,
            ),
            TickerInfo(
                ticker="TSLA", name="Tesla Inc.", sector="Consumer Cyclical",
                earliest_date="2015-01-02", latest_date="2025-12-31", total_candles=2768,
            ),
            TickerInfo(
                ticker="AMZN", name="Amazon.com Inc.", sector="Consumer Cyclical",
                earliest_date="2015-01-02", latest_date="2025-12-31", total_candles=2768,
            ),
        ]
        return AvailableTickers(tickers=tickers)

    async def create_session(
        self, user_id: str, request: SimulationCreateRequest
    ) -> SimulationCreateResponse:
        """Create a new simulation session.
        
        Loads historical data for the ticker and date range,
        prepares the candle queue, and initializes AI competitor state.
        """
        uid = uuid.UUID(user_id)

        # Count available candles in range
        total_candles = await self._count_candles(
            request.ticker, request.start_date, request.end_date
        )
        if total_candles < 10:
            raise ValueError("Insufficient historical data for this date range")

        session = SimulationSession(
            user_id=uid,
            ticker=request.ticker,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            current_capital=request.initial_capital,
            total_candles=total_candles,
            playback_speed=request.playback_speed,
        )
        self.db.add(session)
        await self.db.flush()

        # Prepare candle data in Redis for streaming
        await self._prepare_candle_stream(session)

        ws_url = f"ws://localhost:8000/ws/simulation/{session.id}"

        return SimulationCreateResponse(
            session_id=str(session.id),
            ticker=request.ticker,
            total_candles=total_candles,
            initial_capital=request.initial_capital,
            ws_url=ws_url,
        )

    async def get_state(self, user_id: str, session_id: str) -> SimulationState:
        """Get current simulation state."""
        session = await self._get_session(user_id, session_id)
        current_price = await self._get_candle_price(session)

        portfolio_value = session.current_capital + (session.shares_held * current_price)
        user_pnl = portfolio_value - session.initial_capital
        user_pnl_pct = (user_pnl / session.initial_capital) * 100

        return SimulationState(
            session_id=str(session.id),
            ticker=session.ticker,
            status=session.status,
            current_candle_index=session.current_candle_index,
            total_candles=session.total_candles,
            current_price=current_price,
            cash_balance=session.current_capital,
            shares_held=session.shares_held,
            portfolio_value=portfolio_value,
            user_pnl=user_pnl,
            user_pnl_pct=user_pnl_pct,
            ai_pnl=session.ai_pnl,
            ai_pnl_pct=(session.ai_pnl / session.initial_capital) * 100,
            playback_speed=session.playback_speed,
        )

    async def control(
        self, user_id: str, session_id: str, request: SimulationControlRequest
    ) -> dict:
        """Control simulation playback."""
        session = await self._get_session(user_id, session_id)

        if request.action == "play":
            session.status = "active"
        elif request.action == "pause":
            session.status = "paused"
        elif request.action == "speed" and request.speed:
            session.playback_speed = max(0.25, min(request.speed, 10.0))
        elif request.action == "skip" and request.skip_to is not None:
            session.current_candle_index = min(request.skip_to, session.total_candles - 1)

        await self.db.flush()
        return {"status": session.status, "speed": session.playback_speed}

    async def execute_trade(
        self, user_id: str, session_id: str, request: SimulationTradeRequest
    ) -> SimulationTradeResponse:
        """Execute a trade within a simulation at current candle price."""
        session = await self._get_session(user_id, session_id)
        price = await self._get_candle_price(session)

        total_cost = price * request.quantity
        if request.side == "buy":
            if session.current_capital < total_cost:
                raise ValueError("Insufficient simulation capital")
            session.current_capital -= total_cost
            session.shares_held += request.quantity
        elif request.side == "sell":
            if session.shares_held < request.quantity:
                raise ValueError("Insufficient shares")
            session.current_capital += total_cost
            session.shares_held -= request.quantity

        # Record trade
        trade = Trade(
            user_id=uuid.UUID(user_id),
            session_id=session.id,
            ticker=session.ticker,
            side=request.side,
            quantity=request.quantity,
            price=price,
            total_value=total_cost,
            trade_type="user",
            is_simulated=True,
        )
        self.db.add(trade)

        # AI competitor decision
        ai_action, ai_explanation = await self._ai_decide(session, price)

        portfolio_value = session.current_capital + session.shares_held * price
        pnl = portfolio_value - session.initial_capital

        await self.db.flush()

        return SimulationTradeResponse(
            trade_id=str(trade.id),
            side=request.side,
            quantity=request.quantity,
            price=price,
            cash_balance=session.current_capital,
            shares_held=session.shares_held,
            portfolio_value=portfolio_value,
            pnl=pnl,
            ai_action=ai_action,
            ai_explanation=ai_explanation,
        )

    async def get_result(self, user_id: str, session_id: str) -> SimulationResult:
        """Get final simulation results after completion."""
        session = await self._get_session(user_id, session_id)

        # Count user trades in this session
        result = await self.db.execute(
            select(func.count(Trade.id)).where(
                Trade.session_id == session.id,
                Trade.trade_type == "user",
            )
        )
        user_trades_count = result.scalar() or 0

        last_price = await self._get_candle_price(session)
        user_final = session.current_capital + session.shares_held * last_price
        user_pnl = user_final - session.initial_capital
        user_pnl_pct = (user_pnl / session.initial_capital) * 100

        ai_final = session.initial_capital + session.ai_pnl
        ai_pnl_pct = (session.ai_pnl / session.initial_capital) * 100

        winner = "user" if user_pnl > session.ai_pnl else "ai"
        xp_earned = 50 if winner == "user" else 20

        return SimulationResult(
            session_id=str(session.id),
            ticker=session.ticker,
            duration_candles=session.current_candle_index,
            user_final_value=user_final,
            user_pnl=user_pnl,
            user_pnl_pct=user_pnl_pct,
            user_trades_count=user_trades_count,
            ai_final_value=ai_final,
            ai_pnl=session.ai_pnl,
            ai_pnl_pct=ai_pnl_pct,
            ai_trades_count=len(session.ai_trades or []),
            winner=winner,
            xp_earned=xp_earned,
            explanation=f"{'You' if winner == 'user' else 'The AI'} won this simulation round!",
        )

    # ─── Private ───

    async def _get_session(self, user_id: str, session_id: str) -> SimulationSession:
        session = await self.db.get(SimulationSession, uuid.UUID(session_id))
        if not session or str(session.user_id) != user_id:
            raise ValueError("Session not found")
        return session

    async def _count_candles(self, ticker: str, start_date: str, end_date: str) -> int:
        """Count OHLCV candles in date range. Placeholder."""
        return 252  # ~1 trading year

    async def _prepare_candle_stream(self, session: SimulationSession) -> None:
        """Pre-load candle data into Redis for WebSocket streaming."""
        # TODO: load from TimescaleDB → Redis stream keyed by session_id
        pass

    async def _get_candle_price(self, session: SimulationSession) -> float:
        """Get the close price of the current candle."""
        # TODO: fetch from Redis/TimescaleDB
        return 150.0  # placeholder

    async def _ai_decide(self, session: SimulationSession, price: float) -> tuple[str, str]:
        """AI competitor makes a decision based on LSTM prediction."""
        # TODO: integrate with PredictionService
        return "hold", "AI is waiting for a clearer signal based on RSI and MACD convergence."
