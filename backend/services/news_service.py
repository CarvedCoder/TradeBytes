"""
News Intelligence Service.

Manages news feed, sentiment analysis results, and sentiment-vs-price visualization.
"""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.news import NewsArticle, SentimentTimeSeries
from backend.schemas.news import (
    NewsArticleResponse,
    NewsFeedResponse,
    SentimentTimeSeriesResponse,
    SentimentPricePoint,
    TickerSentimentResponse,
)

logger = structlog.get_logger()


class NewsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_feed(
        self, ticker: str | None, category: str | None, limit: int, offset: int
    ) -> NewsFeedResponse:
        query = select(NewsArticle).order_by(desc(NewsArticle.published_at))
        if ticker:
            query = query.where(NewsArticle.tickers.contains([ticker]))
        if category:
            query = query.where(NewsArticle.categories.contains([category]))

        count_query = select(func.count(NewsArticle.id))
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        articles = result.scalars().all()

        return NewsFeedResponse(
            articles=[
                NewsArticleResponse(
                    id=str(a.id),
                    title=a.title,
                    summary=a.summary,
                    source=a.source,
                    url=a.url,
                    published_at=a.published_at,
                    tickers=a.tickers or [],
                    sentiment_score=a.sentiment_score,
                    sentiment_label=a.sentiment_label,
                    finbert_scores=a.finbert_scores,
                )
                for a in articles
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def get_article(self, article_id: str) -> NewsArticleResponse:
        article = await self.db.get(NewsArticle, uuid.UUID(article_id))
        if not article:
            raise ValueError("Article not found")
        return NewsArticleResponse(
            id=str(article.id),
            title=article.title,
            summary=article.summary,
            source=article.source,
            url=article.url,
            published_at=article.published_at,
            tickers=article.tickers or [],
            sentiment_score=article.sentiment_score,
            sentiment_label=article.sentiment_label,
            finbert_scores=article.finbert_scores,
        )

    async def get_sentiment_timeseries(
        self, ticker: str, days: int
    ) -> SentimentTimeSeriesResponse:
        """Get sentiment time-series overlaid with price data."""
        # TODO: query TimescaleDB for sentiment + price data
        return SentimentTimeSeriesResponse(
            ticker=ticker,
            data_points=[],
        )

    async def get_all_ticker_sentiments(self) -> list[TickerSentimentResponse]:
        """Get current sentiment summary for all tracked tickers."""
        # TODO: aggregate from recent sentiment data
        return []
