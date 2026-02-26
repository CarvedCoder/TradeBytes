"""
Portfolio Analyzer Endpoints.

Provides allocation breakdown, risk metrics, correlation analysis,
drawdown tracking, and AI improvement suggestions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.portfolio import (
    PortfolioOverview,
    RiskMetrics,
    CorrelationMatrix,
    DrawdownAnalysis,
    AIPortfolioSuggestions,
)
from backend.services.portfolio_service import PortfolioService

router = APIRouter()


@router.get("/allocation", response_model=PortfolioOverview)
@router.get("/overview", response_model=PortfolioOverview)
async def get_portfolio_overview(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio overview: positions, allocation, total value, PnL."""
    service = PortfolioService(db)
    return await service.get_overview(user_id)


@router.get("/risk-metrics", response_model=RiskMetrics)
@router.get("/risk", response_model=RiskMetrics, include_in_schema=False)
async def get_risk_metrics(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get risk metrics: volatility, beta, Sharpe ratio, VaR."""
    service = PortfolioService(db)
    return await service.compute_risk_metrics(user_id)


@router.get("/correlation", response_model=CorrelationMatrix)
async def get_correlation_matrix(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get correlation matrix between portfolio holdings."""
    service = PortfolioService(db)
    return await service.compute_correlation(user_id)


@router.get("/drawdown", response_model=DrawdownAnalysis)
async def get_drawdown_analysis(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get drawdown analysis: max drawdown, recovery time, worst periods."""
    service = PortfolioService(db)
    return await service.compute_drawdown(user_id)


@router.get("/ai-suggestions", response_model=AIPortfolioSuggestions)
@router.get("/suggestions", response_model=AIPortfolioSuggestions, include_in_schema=False)
async def get_ai_suggestions(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get AI-generated portfolio improvement suggestions."""
    service = PortfolioService(db)
    return await service.generate_suggestions(user_id)
