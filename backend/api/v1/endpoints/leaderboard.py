"""
Leaderboard Endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.leaderboard import LeaderboardResponse, UserRankResponse
from backend.services.leaderboard_service import LeaderboardService

router = APIRouter()


@router.get("/", response_model=LeaderboardResponse)
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
    period: str = Query(default="weekly", pattern="^(daily|weekly|all_time)$"),
    limit: int = Query(default=50, le=100),
):
    """Get leaderboard rankings for given period."""
    service = LeaderboardService(db)
    return await service.get_leaderboard(period, limit)


@router.get("/me", response_model=UserRankResponse)
async def get_my_rank(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    period: str = Query(default="weekly", pattern="^(daily|weekly|all_time)$"),
):
    """Get current user's rank and nearby players."""
    service = LeaderboardService(db)
    return await service.get_user_rank(user_id, period)
