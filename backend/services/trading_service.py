"""
Trading Service - Execute simulated trades with AI competitor.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.trading import Trade, Portfolio, Position
from backend.schemas.trading import TradeRequest, TradeResponse, TradeHistory, AITradeResult
from backend.services.gamification_service import GamificationService

logger = structlog.get_logger()


class TradingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.gamification = GamificationService(db)

    async def execute_trade(self, user_id: str, request: TradeRequest) -> TradeResponse:
        """Execute a simulated trade and trigger AI competitor."""
        uid = uuid.UUID(user_id)

        # Get portfolio
        result = await self.db.execute(select(Portfolio).where(Portfolio.user_id == uid))
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            portfolio = Portfolio(user_id=uid)
            self.db.add(portfolio)
            await self.db.flush()

        # Get current price (from replay engine or latest data)
        current_price = await self._get_current_price(request.ticker)
        total_value = current_price * request.quantity

        # Validate trade
        if request.side == "buy":
            if portfolio.cash_balance < total_value:
                raise ValueError("Insufficient funds")
            portfolio.cash_balance -= total_value
        elif request.side == "sell":
            position = await self._get_position(portfolio.id, request.ticker)
            if not position or position.shares < request.quantity:
                raise ValueError("Insufficient shares")
            portfolio.cash_balance += total_value

        # Create trade record
        trade = Trade(
            user_id=uid,
            session_id=uuid.UUID(request.session_id) if request.session_id else None,
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            price=current_price,
            total_value=total_value,
            trade_type="user",
        )
        self.db.add(trade)

        # Update position
        await self._update_position(portfolio, request.ticker, request.side, request.quantity, current_price)

        # AI Competitor: get prediction and simulate AI trade
        ai_result = await self._run_ai_competitor(request.ticker, current_price)

        # Generate explanation
        explanation = await self._generate_explanation(trade, ai_result)
        trade.ai_explanation = explanation

        # Gamification
        won_vs_ai = self._did_user_win(request.side, ai_result)
        xp_earned = await self.gamification.record_trade(user_id, won_vs_ai=won_vs_ai)

        await self.db.flush()

        return TradeResponse(
            trade_id=str(trade.id),
            ticker=request.ticker,
            side=request.side,
            quantity=request.quantity,
            price=current_price,
            total_value=total_value,
            ai_trade=ai_result,
            ai_explanation=explanation,
            xp_earned=xp_earned,
        )

    async def get_history(
        self, user_id: str, ticker: str | None, limit: int, offset: int
    ) -> list[TradeHistory]:
        query = select(Trade).where(Trade.user_id == uuid.UUID(user_id))
        if ticker:
            query = query.where(Trade.ticker == ticker)
        query = query.order_by(Trade.created_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        trades = result.scalars().all()
        return [
            TradeHistory(
                trade_id=str(t.id),
                ticker=t.ticker,
                side=t.side,
                quantity=t.quantity,
                price=t.price,
                total_value=t.total_value,
                pnl=t.pnl,
                pnl_pct=t.pnl_pct,
                trade_type=t.trade_type,
                ai_explanation=t.ai_explanation,
                created_at=t.created_at,
            )
            for t in trades
        ]

    async def get_trade_detail(self, user_id: str, trade_id: str) -> TradeHistory:
        trade = await self.db.get(Trade, uuid.UUID(trade_id))
        if not trade or str(trade.user_id) != user_id:
            raise ValueError("Trade not found")
        return TradeHistory(
            trade_id=str(trade.id),
            ticker=trade.ticker,
            side=trade.side,
            quantity=trade.quantity,
            price=trade.price,
            total_value=trade.total_value,
            pnl=trade.pnl,
            pnl_pct=trade.pnl_pct,
            trade_type=trade.trade_type,
            ai_explanation=trade.ai_explanation,
            created_at=trade.created_at,
        )

    # ─── Private ───

    async def _get_current_price(self, ticker: str) -> float:
        """Get current price from cache/DB. In simulation, from replay engine."""
        # TODO: integrate with replay engine or market data cache
        return 100.0  # placeholder

    async def _get_position(self, portfolio_id: uuid.UUID, ticker: str) -> Position | None:
        result = await self.db.execute(
            select(Position).where(
                Position.portfolio_id == portfolio_id,
                Position.ticker == ticker,
            )
        )
        return result.scalar_one_or_none()

    async def _update_position(
        self, portfolio: Portfolio, ticker: str, side: str, quantity: float, price: float
    ) -> None:
        position = await self._get_position(portfolio.id, ticker)
        if not position:
            position = Position(portfolio_id=portfolio.id, ticker=ticker)
            self.db.add(position)

        if side == "buy":
            total_cost = position.avg_cost * position.shares + price * quantity
            position.shares += quantity
            position.avg_cost = total_cost / position.shares if position.shares > 0 else 0
        elif side == "sell":
            position.shares -= quantity
            if position.shares <= 0:
                position.shares = 0
                position.avg_cost = 0

        position.current_price = price
        position.market_value = position.shares * price
        position.unrealized_pnl = (price - position.avg_cost) * position.shares
        position.unrealized_pnl_pct = (
            (price - position.avg_cost) / position.avg_cost * 100
            if position.avg_cost > 0 else 0
        )

    async def _run_ai_competitor(self, ticker: str, current_price: float) -> AITradeResult:
        """Run LSTM prediction and generate AI trade decision."""
        # TODO: integrate with PredictionService
        return AITradeResult(
            side="buy",
            quantity=1.0,
            price=current_price,
            predicted_direction="up",
            confidence=0.72,
            expected_return=0.015,
        )

    async def _generate_explanation(self, trade: Trade, ai_result: AITradeResult) -> str:
        """Generate AI explanation for the trade comparison."""
        # TODO: integrate with ExplanationEngine
        return (
            f"You chose to {trade.side} {trade.ticker} at ${trade.price:.2f}. "
            f"The AI predicted {ai_result.predicted_direction} movement with "
            f"{ai_result.confidence:.0%} confidence and chose to {ai_result.side}."
        )

    def _did_user_win(self, user_side: str, ai_result: AITradeResult) -> bool:
        """Determine if user's trade direction was better than AI's."""
        # Simplified: will be evaluated after next candle arrives
        return user_side == ai_result.side
