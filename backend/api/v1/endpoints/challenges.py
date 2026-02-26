"""
Daily Challenges Endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.challenges import (
    DailyChallengeResponse,
    ChallengeAttemptRequest,
    ChallengeAttemptResponse,
    ChallengeHistoryResponse,
)
from backend.services.challenge_service import ChallengeService

router = APIRouter()


@router.get("/today", response_model=DailyChallengeResponse)
async def get_today_challenge(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get today's daily challenge (theory + simulation + prediction)."""
    service = ChallengeService(db)
    try:
        return await service.get_today(user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/attempt", response_model=ChallengeAttemptResponse)
async def submit_challenge_attempt(
    attempt: ChallengeAttemptRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit daily challenge attempt.
    
    Evaluates all three components, awards XP, updates streak.
    """
    service = ChallengeService(db)
    return await service.submit_attempt(user_id, attempt)


@router.get("/history", response_model=list[ChallengeHistoryResponse])
async def get_challenge_history(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
    limit: int = 30,
):
    """Get past challenge attempts and results."""
    service = ChallengeService(db)
    return await service.get_history(user_id, limit)
