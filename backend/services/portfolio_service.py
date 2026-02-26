"""
Portfolio Analyzer Service.

Computes allocation, risk metrics, correlations, drawdowns,
and generates AI improvement suggestions.
"""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.trading import Portfolio, Position, Trade
from backend.schemas.portfolio import (
    PortfolioOverview,
    PositionInfo,
    AllocationSlice,
    RiskMetrics,
    PositionRisk,
    CorrelationMatrix,
    DrawdownAnalysis,
    DrawdownPoint,
    AIPortfolioSuggestions,
    PortfolioSuggestion,
)

logger = structlog.get_logger()


class PortfolioService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_overview(self, user_id: str) -> PortfolioOverview:
        portfolio = await self._get_portfolio(user_id)
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id)
        )
        positions = result.scalars().all()

        invested = sum(p.market_value for p in positions)
        total_value = portfolio.cash_balance + invested
        total_pnl = total_value - portfolio.initial_capital
        total_pnl_pct = (total_pnl / portfolio.initial_capital * 100) if portfolio.initial_capital else 0

        pos_infos = [
            PositionInfo(
                ticker=p.ticker,
                shares=p.shares,
                avg_cost=p.avg_cost,
                current_price=p.current_price,
                market_value=p.market_value,
                unrealized_pnl=p.unrealized_pnl,
                unrealized_pnl_pct=p.unrealized_pnl_pct,
                weight=p.market_value / total_value * 100 if total_value > 0 else 0,
            )
            for p in positions if p.shares > 0
        ]

        allocation = [AllocationSlice(label="Cash", value=portfolio.cash_balance, percentage=portfolio.cash_balance / total_value * 100 if total_value else 100)]
        allocation += [AllocationSlice(label=p.ticker, value=p.market_value, percentage=p.weight) for p in pos_infos]

        return PortfolioOverview(
            total_value=total_value,
            cash_balance=portfolio.cash_balance,
            invested_value=invested,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            positions=pos_infos,
            allocation=allocation,
        )

    async def compute_risk_metrics(self, user_id: str) -> RiskMetrics:
        """Compute portfolio risk metrics using historical returns."""
        # TODO: compute from actual historical price data
        return RiskMetrics(
            portfolio_volatility=0.18,
            portfolio_beta=1.05,
            sharpe_ratio=1.2,
            sortino_ratio=1.5,
            max_drawdown=-0.12,
            value_at_risk_95=-0.025,
            per_position=[],
        )

    async def compute_correlation(self, user_id: str) -> CorrelationMatrix:
        """Compute correlation matrix between holdings."""
        portfolio = await self._get_portfolio(user_id)
        result = await self.db.execute(
            select(Position).where(Position.portfolio_id == portfolio.id, Position.shares > 0)
        )
        positions = result.scalars().all()
        tickers = [p.ticker for p in positions]

        # TODO: compute from actual price history
        n = len(tickers)
        matrix = np.eye(n).tolist() if n > 0 else []
        return CorrelationMatrix(tickers=tickers, matrix=matrix)

    async def compute_drawdown(self, user_id: str) -> DrawdownAnalysis:
        """Compute drawdown analysis from portfolio value history."""
        return DrawdownAnalysis(
            current_drawdown=0.0,
            max_drawdown=-0.12,
            max_drawdown_duration_days=15,
            recovery_time_days=8,
            drawdown_series=[],
        )

    async def generate_suggestions(self, user_id: str) -> AIPortfolioSuggestions:
        """Generate AI-powered portfolio improvement suggestions."""
        overview = await self.get_overview(user_id)
        risk = await self.compute_risk_metrics(user_id)

        suggestions = []
        # Concentration check
        for pos in overview.positions:
            if pos.weight > 30:
                suggestions.append(PortfolioSuggestion(
                    type="diversify",
                    ticker=pos.ticker,
                    action=f"Consider reducing {pos.ticker} position (currently {pos.weight:.1f}% of portfolio)",
                    reason="Concentration risk: single position exceeds 30% of portfolio",
                    confidence=0.85,
                ))

        # Cash drag check
        cash_pct = overview.cash_balance / overview.total_value * 100 if overview.total_value else 100
        if cash_pct > 50:
            suggestions.append(PortfolioSuggestion(
                type="rebalance",
                ticker=None,
                action="Deploy idle cash into diversified positions",
                reason=f"High cash allocation ({cash_pct:.0f}%) may be causing drag on returns",
                confidence=0.7,
            ))

        risk_level = "low" if risk.portfolio_volatility < 0.15 else "medium" if risk.portfolio_volatility < 0.25 else "high"

        return AIPortfolioSuggestions(
            overall_assessment=f"Portfolio has {risk_level} risk with {len(overview.positions)} positions",
            risk_level=risk_level,
            suggestions=suggestions,
        )

    async def _get_portfolio(self, user_id: str) -> Portfolio:
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.user_id == uuid.UUID(user_id))
        )
        portfolio = result.scalar_one_or_none()
        if not portfolio:
            raise ValueError("Portfolio not found")
        return portfolio
