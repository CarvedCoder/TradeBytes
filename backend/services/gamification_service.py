"""
Gamification Engine - Backend-driven XP, Streaks, Levels, Badges.

Core formulas:
- XP per trade: base_xp * (1 + streak_multiplier)
- Level threshold: 100 * level^1.5
- Streak multiplier: min(streak * 0.1, 2.0) → max 3x
- Leaderboard score: xp_total * 0.5 + wins_vs_ai * 100 + streak * 50
"""

from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.gamification import UserGamification, DailyChallengeAttempt
from backend.schemas.gamification import (
    GamificationState,
    XPTransaction,
    BadgeInfo,
    BadgeList,
    ProgressBar,
    FeatureUnlockStatus,
    FeatureUnlock,
)

logger = structlog.get_logger()

# ─── Constants ───

LEVEL_BASE_XP = 100
LEVEL_EXPONENT = 1.5
MAX_STREAK_MULTIPLIER = 2.0
STREAK_MULTIPLIER_STEP = 0.1

XP_REWARDS = {
    "trade_executed": 10,
    "trade_win_vs_ai": 50,
    "daily_challenge_complete": 50,
    "daily_challenge_perfect": 100,
    "module_complete": 25,
    "path_complete": 200,
    "streak_bonus_per_day": 5,
    "first_trade": 100,
    "first_simulation": 75,
}

LEVEL_NAMES = {
    1: "Novice Trader",
    5: "Market Analyst",
    10: "Portfolio Manager",
    15: "Senior Strategist",
    20: "Hedge Fund Manager",
    25: "Market Wizard",
    30: "Wall Street Legend",
    40: "Financial Oracle",
    50: "Master of Markets",
}

BADGES = {
    "first_blood": {"name": "First Blood", "desc": "Execute your first trade", "icon": "⚔️", "condition": "total_trades >= 1"},
    "winning_streak_3": {"name": "Hot Streak", "desc": "Beat AI 3 times in a row", "icon": "🔥", "condition": "consecutive_wins >= 3"},
    "streak_7": {"name": "Weekly Warrior", "desc": "7-day activity streak", "icon": "📅", "condition": "current_streak >= 7"},
    "streak_30": {"name": "Monthly Master", "desc": "30-day activity streak", "icon": "🏆", "condition": "current_streak >= 30"},
    "level_10": {"name": "Decade Club", "desc": "Reach level 10", "icon": "🎯", "condition": "level >= 10"},
    "trades_100": {"name": "Centurion", "desc": "Execute 100 trades", "icon": "💯", "condition": "total_trades >= 100"},
    "ai_slayer": {"name": "AI Slayer", "desc": "Beat AI 50 times", "icon": "🤖", "condition": "total_wins_vs_ai >= 50"},
    "scholar": {"name": "Scholar", "desc": "Complete all basic learning paths", "icon": "📚", "condition": "basic_paths_complete"},
    "daily_devotee": {"name": "Daily Devotee", "desc": "Complete 30 daily challenges", "icon": "📆", "condition": "daily_challenges_completed >= 30"},
}

FEATURE_UNLOCKS = {
    "stock_playground": {"name": "Stock Playground", "path": None, "level": 1},
    "daily_challenges": {"name": "Daily Challenges", "path": None, "level": 2},
    "ai_competitor": {"name": "AI Competitor", "path": "basics-of-trading", "level": 3},
    "portfolio_analyzer": {"name": "Portfolio Analyzer", "path": "portfolio-management", "level": 5},
    "news_intelligence": {"name": "News Intelligence", "path": "market-analysis", "level": 7},
    "ai_advisor": {"name": "AI Advisor", "path": "advanced-strategies", "level": 10},
    "community_chat": {"name": "Community Chat", "path": None, "level": 3},
    "advanced_charts": {"name": "Advanced Charts", "path": "technical-analysis", "level": 8},
}


class GamificationService:
    """Core gamification engine - all XP/level/streak logic is here."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── XP & Level Calculations ───

    @staticmethod
    def xp_for_level(level: int) -> int:
        """Calculate cumulative XP needed to reach a level."""
        return int(LEVEL_BASE_XP * (level ** LEVEL_EXPONENT))

    @staticmethod
    def level_from_xp(xp: int) -> int:
        """Calculate level from total XP."""
        level = 1
        while GamificationService.xp_for_level(level + 1) <= xp:
            level += 1
        return level

    @staticmethod
    def streak_multiplier(streak: int) -> float:
        """Calculate XP multiplier from current streak."""
        return 1.0 + min(streak * STREAK_MULTIPLIER_STEP, MAX_STREAK_MULTIPLIER)

    @staticmethod
    def leaderboard_score(xp: int, wins: int, streak: int) -> int:
        """Calculate composite leaderboard score."""
        return int(xp * 0.5 + wins * 100 + streak * 50)

    @staticmethod
    def level_name(level: int) -> str:
        """Get the title for a given level."""
        name = "Novice Trader"
        for threshold, title in sorted(LEVEL_NAMES.items()):
            if level >= threshold:
                name = title
        return name

    # ─── Core Operations ───

    async def award_xp(self, user_id: str, amount: int, reason: str, source: str) -> int:
        """Award XP to a user with streak multiplier applied.
        
        Returns the actual XP awarded (after multiplier).
        """
        gam = await self._get_or_create(user_id)
        multiplier = self.streak_multiplier(gam.current_streak)
        actual_xp = int(amount * multiplier)

        gam.xp_total += actual_xp
        gam.level = self.level_from_xp(gam.xp_total)
        await self.db.flush()

        logger.info(
            "XP awarded",
            user_id=user_id,
            base=amount,
            multiplier=multiplier,
            actual=actual_xp,
            reason=reason,
        )
        return actual_xp

    async def update_streak(self, user_id: str) -> int:
        """Update daily activity streak. Call on any qualifying activity.
        
        Returns updated streak count.
        """
        gam = await self._get_or_create(user_id)
        today = date.today()

        if gam.last_activity_date == today:
            return gam.current_streak  # Already counted today

        if gam.last_activity_date == today.replace(day=today.day - 1) if today.day > 1 else None:
            # Consecutive day
            gam.current_streak += 1
        else:
            # Streak broken or first activity
            gam.current_streak = 1

        gam.last_activity_date = today
        if gam.current_streak > gam.longest_streak:
            gam.longest_streak = gam.current_streak

        # Award streak bonus XP
        if gam.current_streak > 1:
            bonus = XP_REWARDS["streak_bonus_per_day"] * gam.current_streak
            gam.xp_total += bonus

        await self.db.flush()
        return gam.current_streak

    async def record_trade(self, user_id: str, won_vs_ai: bool = False) -> int:
        """Record a trade for gamification tracking. Returns XP earned."""
        gam = await self._get_or_create(user_id)
        gam.total_trades += 1

        xp = XP_REWARDS["trade_executed"]
        if gam.total_trades == 1:
            xp += XP_REWARDS["first_trade"]

        if won_vs_ai:
            gam.total_wins_vs_ai += 1
            xp += XP_REWARDS["trade_win_vs_ai"]

        actual_xp = await self.award_xp(user_id, xp, "trade", "trade")
        await self.update_streak(user_id)
        await self._check_badges(gam)

        return actual_xp

    async def record_challenge_complete(
        self, user_id: str, perfect: bool = False
    ) -> int:
        """Record daily challenge completion. Returns XP earned."""
        gam = await self._get_or_create(user_id)
        gam.daily_challenges_completed += 1

        xp = XP_REWARDS["daily_challenge_perfect" if perfect else "daily_challenge_complete"]
        actual_xp = await self.award_xp(user_id, xp, "daily_challenge", "challenge")
        await self.update_streak(user_id)
        await self._check_badges(gam)

        return actual_xp

    # ─── State Queries ───

    async def get_state(self, user_id: str) -> GamificationState:
        gam = await self._get_or_create(user_id)
        current_level_xp = self.xp_for_level(gam.level)
        next_level_xp = self.xp_for_level(gam.level + 1)
        xp_to_next = next_level_xp - gam.xp_total

        badges = self._evaluate_badges(gam)
        earned_badges = [b for b in badges if b.earned]

        progress_bars = [
            ProgressBar(
                label="Level Progress",
                current=gam.xp_total - current_level_xp,
                target=next_level_xp - current_level_xp,
                percentage=min((gam.xp_total - current_level_xp) / max(next_level_xp - current_level_xp, 1) * 100, 100),
            ),
            ProgressBar(
                label="Daily Streak",
                current=gam.current_streak,
                target=max(gam.longest_streak, 7),
                percentage=min(gam.current_streak / max(gam.longest_streak, 7) * 100, 100),
            ),
        ]

        return GamificationState(
            user_id=user_id,
            xp_total=gam.xp_total,
            xp_to_next_level=max(xp_to_next, 0),
            level=gam.level,
            level_name=self.level_name(gam.level),
            current_streak=gam.current_streak,
            longest_streak=gam.longest_streak,
            daily_challenge_available=gam.last_activity_date != date.today(),
            badges=earned_badges,
            unlocked_features=gam.unlocked_features or [],
            progress_bars=progress_bars,
        )

    async def get_xp_history(self, user_id: str, limit: int) -> list[XPTransaction]:
        # In production, this would query an XP transaction log table
        return []

    async def get_badges(self, user_id: str) -> BadgeList:
        gam = await self._get_or_create(user_id)
        badges = self._evaluate_badges(gam)
        return BadgeList(
            earned=[b for b in badges if b.earned],
            in_progress=[b for b in badges if not b.earned and b.progress > 0],
            locked=[b for b in badges if not b.earned and b.progress == 0],
        )

    async def get_unlock_status(self, user_id: str) -> FeatureUnlockStatus:
        gam = await self._get_or_create(user_id)
        unlocked_set = set(gam.unlocked_features or [])

        unlocked = []
        locked = []
        for feat_id, feat in FEATURE_UNLOCKS.items():
            unlock = FeatureUnlock(
                feature_id=feat_id,
                name=feat["name"],
                description=f"Unlocks at level {feat['level']}" + (f" after completing {feat['path']}" if feat['path'] else ""),
                required_path=feat["path"],
                is_unlocked=feat_id in unlocked_set or gam.level >= feat["level"],
            )
            if unlock.is_unlocked:
                unlocked.append(unlock)
            else:
                locked.append(unlock)

        return FeatureUnlockStatus(unlocked=unlocked, locked=locked)

    # ─── Private Helpers ───

    async def _get_or_create(self, user_id: str) -> UserGamification:
        result = await self.db.execute(
            select(UserGamification).where(UserGamification.user_id == uuid.UUID(user_id))
        )
        gam = result.scalar_one_or_none()
        if not gam:
            gam = UserGamification(user_id=uuid.UUID(user_id))
            self.db.add(gam)
            await self.db.flush()
        return gam

    def _evaluate_badges(self, gam: UserGamification) -> list[BadgeInfo]:
        badges = []
        for badge_id, badge in BADGES.items():
            earned = badge_id in (gam.badges or {})
            progress = 0.0

            # Calculate progress based on condition
            if "total_trades" in badge["condition"]:
                target = int(badge["condition"].split(">=")[1].strip())
                progress = min(gam.total_trades / target, 1.0)
            elif "current_streak" in badge["condition"]:
                target = int(badge["condition"].split(">=")[1].strip())
                progress = min(gam.current_streak / target, 1.0)
            elif "level" in badge["condition"]:
                target = int(badge["condition"].split(">=")[1].strip())
                progress = min(gam.level / target, 1.0)
            elif "total_wins_vs_ai" in badge["condition"]:
                target = int(badge["condition"].split(">=")[1].strip())
                progress = min(gam.total_wins_vs_ai / target, 1.0)

            badges.append(BadgeInfo(
                id=badge_id,
                name=badge["name"],
                description=badge["desc"],
                icon=badge["icon"],
                earned=earned or progress >= 1.0,
                progress=progress,
            ))
        return badges

    async def _check_badges(self, gam: UserGamification) -> None:
        """Check and award any newly earned badges."""
        if gam.badges is None:
            gam.badges = {}

        for badge_id, badge in BADGES.items():
            if badge_id in gam.badges:
                continue

            earned = False
            cond = badge["condition"]
            if "total_trades >= " in cond:
                target = int(cond.split(">=")[1].strip())
                earned = gam.total_trades >= target
            elif "current_streak >= " in cond:
                target = int(cond.split(">=")[1].strip())
                earned = gam.current_streak >= target
            elif "level >= " in cond:
                target = int(cond.split(">=")[1].strip())
                earned = gam.level >= target
            elif "total_wins_vs_ai >= " in cond:
                target = int(cond.split(">=")[1].strip())
                earned = gam.total_wins_vs_ai >= target

            if earned:
                gam.badges[badge_id] = datetime.now(timezone.utc).isoformat()
                logger.info("Badge earned", badge=badge_id, user_id=str(gam.user_id))
