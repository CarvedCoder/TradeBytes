"""
Models Package - Re-exports all ORM models for Alembic and application usage.
"""

from backend.models.user import User, Passkey, Web3Wallet, WebAuthnChallenge
from backend.models.gamification import (
    UserGamification,
    LearningPath,
    LearningModule,
    UserLearningProgress,
    DailyChallenge,
    DailyChallengeAttempt,
    LeaderboardEntry,
)
from backend.models.trading import (
    Portfolio,
    Position,
    Trade,
    SimulationSession,
    OHLCVCandle,
    TechnicalIndicator,
)
from backend.models.news import (
    NewsArticle,
    SentimentTimeSeries,
    ModelMetadata,
    FeatureMetadata,
    ChatMessage,
)
from backend.models.alerts import Alert, AlertAudit

__all__ = [
    "User",
    "Passkey",
    "Web3Wallet",
    "WebAuthnChallenge",
    "UserGamification",
    "LearningPath",
    "LearningModule",
    "UserLearningProgress",
    "DailyChallenge",
    "DailyChallengeAttempt",
    "LeaderboardEntry",
    "Portfolio",
    "Position",
    "Trade",
    "SimulationSession",
    "OHLCVCandle",
    "TechnicalIndicator",
    "NewsArticle",
    "SentimentTimeSeries",
    "ModelMetadata",
    "FeatureMetadata",
    "ChatMessage",
    "Alert",
    "AlertAudit",
]
