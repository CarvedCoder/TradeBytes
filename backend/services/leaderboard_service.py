"""Leaderboard Service."""
from __future__ import annotations
import uuid
import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.gamification import LeaderboardEntry, UserGamification
from backend.models.user import User
from backend.schemas.leaderboard import LeaderboardResponse, LeaderboardEntryResponse, UserRankResponse

logger = structlog.get_logger()


class LeaderboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_leaderboard(self, period: str, limit: int) -> LeaderboardResponse:
        result = await self.db.execute(
            select(LeaderboardEntry, User)
            .join(User, LeaderboardEntry.user_id == User.id)
            .where(LeaderboardEntry.period == period)
            .order_by(LeaderboardEntry.rank)
            .limit(limit)
        )
        rows = result.all()
        count_result = await self.db.execute(
            select(func.count(LeaderboardEntry.id)).where(LeaderboardEntry.period == period)
        )
        total = count_result.scalar() or 0

        entries = [
            LeaderboardEntryResponse(
                rank=entry.rank, user_id=str(entry.user_id),
                username=user.username, display_name=user.display_name,
                avatar_url=user.avatar_url, score=entry.score,
                xp_earned=entry.xp_earned, trades_won=entry.trades_won,
                streak=entry.streak, level=1,
            )
            for entry, user in rows
        ]
        return LeaderboardResponse(period=period, entries=entries, total_participants=total)

    async def get_user_rank(self, user_id: str, period: str) -> UserRankResponse:
        result = await self.db.execute(
            select(LeaderboardEntry).where(
                LeaderboardEntry.user_id == uuid.UUID(user_id),
                LeaderboardEntry.period == period,
            )
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return UserRankResponse(rank=0, total_participants=0, score=0, percentile=0, nearby=[])

        total_result = await self.db.execute(
            select(func.count(LeaderboardEntry.id)).where(LeaderboardEntry.period == period)
        )
        total = total_result.scalar() or 1
        percentile = (1 - entry.rank / total) * 100

        # Nearby entries
        nearby_result = await self.db.execute(
            select(LeaderboardEntry, User)
            .join(User, LeaderboardEntry.user_id == User.id)
            .where(
                LeaderboardEntry.period == period,
                LeaderboardEntry.rank.between(max(1, entry.rank - 5), entry.rank + 5),
            )
            .order_by(LeaderboardEntry.rank)
        )
        nearby = [
            LeaderboardEntryResponse(
                rank=e.rank, user_id=str(e.user_id),
                username=u.username, display_name=u.display_name,
                avatar_url=u.avatar_url, score=e.score,
                xp_earned=e.xp_earned, trades_won=e.trades_won,
                streak=e.streak, level=1,
            )
            for e, u in nearby_result.all()
        ]
        return UserRankResponse(rank=entry.rank, total_participants=total, score=entry.score, percentile=percentile, nearby=nearby)
