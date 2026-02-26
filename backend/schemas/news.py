"""
News Schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class NewsArticleResponse(BaseModel):
    id: str
    title: str
    summary: str | None
    source: str
    url: str
    published_at: datetime
    tickers: list[str]
    sentiment_score: float | None
    sentiment_label: str | None
    finbert_scores: dict | None = None

    model_config = {"from_attributes": True}


class NewsFeedResponse(BaseModel):
    articles: list[NewsArticleResponse]
    total: int
    offset: int
    limit: int


class SentimentTimeSeriesResponse(BaseModel):
    ticker: str
    data_points: list[SentimentPricePoint]


class SentimentPricePoint(BaseModel):
    date: str
    sentiment: float
    price: float
    article_count: int


class TickerSentimentResponse(BaseModel):
    ticker: str
    current_sentiment: float
    trend: str  # "improving", "declining", "stable"
    article_count_24h: int
    top_headline: str | None
