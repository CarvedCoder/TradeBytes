"""
Financial News Intelligence Endpoints.

Fetches news articles, displays sentiment analysis,
ticker mapping, and sentiment-vs-price visualization data.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import get_current_user_id
from backend.schemas.news import (
    NewsArticleResponse,
    SentimentTimeSeriesResponse,
    TickerSentimentResponse,
    NewsFeedResponse,
)
from backend.services.news_service import NewsService

router = APIRouter()


@router.get("/feed", response_model=NewsFeedResponse)
async def get_news_feed(
    db: AsyncSession = Depends(get_db),
    ticker: str | None = None,
    category: str | None = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
):
    """Get paginated news feed, optionally filtered by ticker or category."""
    service = NewsService(db)
    return await service.get_feed(ticker=ticker, category=category, limit=limit, offset=offset)


@router.get("/article/{article_id}", response_model=NewsArticleResponse)
async def get_article(
    article_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific news article with full sentiment analysis."""
    service = NewsService(db)
    return await service.get_article(article_id)


@router.get("/sentiment/{ticker}", response_model=SentimentTimeSeriesResponse)
async def get_sentiment_timeseries(
    ticker: str,
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, le=365),
):
    """Get sentiment time-series for a ticker overlaid with price data."""
    service = NewsService(db)
    return await service.get_sentiment_timeseries(ticker, days)


@router.get("/ticker-sentiment", response_model=list[TickerSentimentResponse])
async def get_all_ticker_sentiments(
    db: AsyncSession = Depends(get_db),
):
    """Get current sentiment summary for all tracked tickers."""
    service = NewsService(db)
    return await service.get_all_ticker_sentiments()
