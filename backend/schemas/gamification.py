"""
Gamification Schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GamificationState(BaseModel):
    user_id: str
    xp_total: int
    xp_to_next_level: int
    level: int
    level_name: str
    current_streak: int
    longest_streak: int
    daily_challenge_available: bool
    badges: list[BadgeInfo]
    unlocked_features: list[str]
    leaderboard_rank: int | None = None
    progress_bars: list[ProgressBar]


class BadgeInfo(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    earned: bool
    earned_at: datetime | None = None
    progress: float = 0.0  # 0.0 to 1.0


class BadgeList(BaseModel):
    earned: list[BadgeInfo]
    in_progress: list[BadgeInfo]
    locked: list[BadgeInfo]


class ProgressBar(BaseModel):
    label: str
    current: int
    target: int
    percentage: float


class XPTransaction(BaseModel):
    amount: int
    reason: str
    source: str  # "trade", "challenge", "learning", "streak_bonus"
    timestamp: datetime


class FeatureUnlockStatus(BaseModel):
    unlocked: list[FeatureUnlock]
    locked: list[FeatureUnlock]


class FeatureUnlock(BaseModel):
    feature_id: str
    name: str
    description: str
    required_path: str | None = None
    is_unlocked: bool
