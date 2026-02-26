"""
Database Models - News, Sentiment, and AI Metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class NewsArticle(Base):
    """Financial news articles with NLP-derived metadata."""

    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    tickers: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)

    # NLP-derived fields
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 to 1.0
    sentiment_label: Mapped[str | None] = mapped_column(String(20), nullable=True)  # positive, negative, neutral
    finbert_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {positive, negative, neutral}
    entities: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # named entities
    embedding_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # vector DB reference

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class SentimentTimeSeries(Base):
    """Aggregated sentiment scores per ticker per time period - TimescaleDB."""

    __tablename__ = "sentiment_timeseries"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    avg_sentiment: Mapped[float] = mapped_column(Float, nullable=False)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    positive_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    negative_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    neutral_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    weighted_sentiment: Mapped[float] = mapped_column(Float, default=0.0)


class ModelMetadata(Base):
    """ML model registry metadata."""

    __tablename__ = "model_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)  # lstm, finbert, etc.
    ticker: Mapped[str | None] = mapped_column(String(10), nullable=True)
    architecture: Mapped[dict] = mapped_column(JSONB, default=dict)
    hyperparameters: Mapped[dict] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict)  # accuracy, loss, sharpe, etc.
    training_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FeatureMetadata(Base):
    """Feature store metadata - tracks feature versions and schemas."""

    __tablename__ = "feature_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_set_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    features: Mapped[list] = mapped_column(JSONB, nullable=False)  # [{name, dtype, description}]
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    update_frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # "realtime", "hourly", "daily"
    schema_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ChatMessage(Base):
    """Community chat messages."""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # "general", "AAPL", "BTC"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(20), default="text")  # text, trade_share, prediction
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
