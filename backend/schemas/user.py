"""
User Schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    user_id: str
    username: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    level: int
    xp_total: int
    current_streak: int
    longest_streak: int
    total_trades: int
    win_rate: float = 0.0
    member_since: datetime
    badges: list[str] = []

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=1, max_length=100)
    avatar_url: str | None = None
