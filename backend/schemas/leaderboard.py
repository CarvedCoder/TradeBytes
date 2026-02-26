"""
Leaderboard Schemas.
"""

from __future__ import annotations

from pydantic import BaseModel


class LeaderboardResponse(BaseModel):
    period: str
    entries: list[LeaderboardEntryResponse]
    total_participants: int


class LeaderboardEntryResponse(BaseModel):
    rank: int
    user_id: str
    username: str
    display_name: str
    avatar_url: str | None
    score: int
    xp_earned: int
    trades_won: int
    streak: int
    level: int


class UserRankResponse(BaseModel):
    rank: int
    total_participants: int
    score: int
    percentile: float
    nearby: list[LeaderboardEntryResponse]  # ±5 positions around user
