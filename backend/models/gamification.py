"""
Database Models - Gamification System.

Backend-driven XP, streaks, levels, learning paths, daily challenges, and leaderboard.
All gamification logic is computed server-side, not cosmetic.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class UserGamification(Base):
    """Core gamification state per user."""

    __tablename__ = "user_gamification"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    xp_total: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0)
    last_activity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    daily_challenges_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    total_wins_vs_ai: Mapped[int] = mapped_column(Integer, default=0)
    badges: Mapped[dict] = mapped_column(JSONB, default=dict)
    unlocked_features: Mapped[list] = mapped_column(JSONB, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="gamification")


class LearningPath(Base):
    """Structured learning paths that unlock features."""

    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)  # "basics", "technical", "advanced"
    order: Mapped[int] = mapped_column(Integer, default=0)
    xp_reward: Mapped[int] = mapped_column(Integer, default=100)
    prerequisite_path_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id"), nullable=True
    )
    unlocks_feature: Mapped[str | None] = mapped_column(String(100), nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)  # lessons, quizzes, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    modules: Mapped[list["LearningModule"]] = relationship(back_populates="path")


class LearningModule(Base):
    """Individual module within a learning path."""

    __tablename__ = "learning_modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    module_type: Mapped[str] = mapped_column(String(30), nullable=False)  # "lesson", "quiz", "simulation"
    order: Mapped[int] = mapped_column(Integer, default=0)
    content: Mapped[dict] = mapped_column(JSONB, default=dict)
    xp_reward: Mapped[int] = mapped_column(Integer, default=25)

    path: Mapped["LearningPath"] = relationship(back_populates="modules")


class UserLearningProgress(Base):
    """Tracks user progress through learning paths and modules."""

    __tablename__ = "user_learning_progress"
    __table_args__ = (UniqueConstraint("user_id", "module_id", name="uq_user_module"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    path_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("learning_modules.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="not_started")  # not_started, in_progress, completed
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="learning_progress")


class DailyChallenge(Base):
    """Daily challenge definitions: theory + simulation + prediction."""

    __tablename__ = "daily_challenges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    challenge_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium")

    # Theory component
    theory_question: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {question, options, correct, explanation}

    # Simulation component
    simulation_config: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {ticker, start_date, end_date, capital}

    # Prediction component
    prediction_config: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {ticker, target_date, metric}

    xp_reward: Mapped[int] = mapped_column(Integer, default=50)
    bonus_xp: Mapped[int] = mapped_column(Integer, default=25)  # for streak bonus
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DailyChallengeAttempt(Base):
    """Tracks user attempts at daily challenges."""

    __tablename__ = "daily_challenge_attempts"
    __table_args__ = (UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    challenge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("daily_challenges.id", ondelete="CASCADE"), nullable=False
    )
    theory_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    simulation_pnl: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    results: Mapped[dict] = mapped_column(JSONB, default=dict)


class LeaderboardEntry(Base):
    """Materialized leaderboard entries, updated periodically."""

    __tablename__ = "leaderboard"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # "daily", "weekly", "all_time"
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    xp_earned: Mapped[int] = mapped_column(Integer, default=0)
    trades_won: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        UniqueConstraint("user_id", "period", "period_start", name="uq_leaderboard_entry"),
    )
