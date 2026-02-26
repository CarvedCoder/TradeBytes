"""
User Service.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.user import User
from backend.models.gamification import UserGamification
from backend.schemas.user import UserProfile, UserProfileUpdate

logger = structlog.get_logger()


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user_id: str) -> UserProfile:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.gamification))
            .where(User.id == uuid.UUID(user_id))
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        gam = user.gamification
        win_rate = (gam.total_wins_vs_ai / gam.total_trades * 100) if gam and gam.total_trades > 0 else 0.0

        return UserProfile(
            user_id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            avatar_url=user.avatar_url,
            level=gam.level if gam else 1,
            xp_total=gam.xp_total if gam else 0,
            current_streak=gam.current_streak if gam else 0,
            longest_streak=gam.longest_streak if gam else 0,
            total_trades=gam.total_trades if gam else 0,
            win_rate=win_rate,
            member_since=user.created_at,
            badges=list(gam.badges.keys()) if gam and gam.badges else [],
        )

    async def update_profile(self, user_id: str, update: UserProfileUpdate) -> UserProfile:
        user = await self.db.get(User, uuid.UUID(user_id))
        if not user:
            raise ValueError("User not found")

        if update.display_name is not None:
            user.display_name = update.display_name
        if update.avatar_url is not None:
            user.avatar_url = update.avatar_url

        await self.db.flush()
        return await self.get_profile(user_id)

    async def get_public_profile(self, username: str) -> UserProfile:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.gamification))
            .where(User.username == username)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        gam = user.gamification
        return UserProfile(
            user_id=str(user.id),
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            level=gam.level if gam else 1,
            xp_total=gam.xp_total if gam else 0,
            current_streak=gam.current_streak if gam else 0,
            longest_streak=gam.longest_streak if gam else 0,
            total_trades=gam.total_trades if gam else 0,
            win_rate=0.0,
            member_since=user.created_at,
            badges=list(gam.badges.keys()) if gam and gam.badges else [],
        )
