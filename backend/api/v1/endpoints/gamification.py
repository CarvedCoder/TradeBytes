"""
Gamification Endpoints - XP, Levels, Streaks, Badges.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.gamification import (
    GamificationState,
    XPTransaction,
    BadgeList,
    FeatureUnlockStatus,
)
from backend.services.gamification_service import GamificationService

router = APIRouter()


@router.get("/state", response_model=GamificationState)
async def get_gamification_state(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get complete gamification state: XP, level, streak, badges, unlocks."""
    service = GamificationService(db)
    return await service.get_state(user_id)


@router.get("/xp/history", response_model=list[XPTransaction])
async def get_xp_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
):
    """Get recent XP earning history."""
    service = GamificationService(db)
    return await service.get_xp_history(user_id, limit)


@router.get("/badges", response_model=BadgeList)
async def get_badges(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get all earned badges and progress toward next badges."""
    service = GamificationService(db)
    return await service.get_badges(user_id)


@router.get("/unlocks", response_model=FeatureUnlockStatus)
async def get_feature_unlocks(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Check which features the user has unlocked through learning paths."""
    service = GamificationService(db)
    return await service.get_unlock_status(user_id)
