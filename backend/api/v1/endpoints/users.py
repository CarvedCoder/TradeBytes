"""
User Profile Endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.user import UserProfile, UserProfileUpdate
from backend.services.user_service import UserService

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's profile with gamification stats."""
    service = UserService(db)
    return await service.get_profile(user_id)


@router.patch("/me", response_model=UserProfile)
async def update_profile(
    update: UserProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    service = UserService(db)
    return await service.update_profile(user_id, update)


@router.get("/{username}", response_model=UserProfile)
async def get_public_profile(
    username: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a user's public profile."""
    service = UserService(db)
    return await service.get_public_profile(username)
