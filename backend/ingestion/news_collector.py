"""
News & Sentiment Collector.

Fetches financial news and runs sentiment analysis:
- News sources: NewsAPI, RSS feeds, Alpha Vantage news
- Sentiment: FinBERT transformer model
- Entity extraction: Ticker mention detection
- Output: Redis Stream → Database + Feature Store
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.redis import RedisManager

logger = structlog.get_logger()

# Common ticker patterns for entity extraction
TICKER_PATTERN = re.compile(r'\b([A-Z]{1,5})\b')

KNOWN_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA",
    "JPM", "V", "WMT", "JNJ", "PG", "XOM", "UNH", "HD", "MA", "BAC",
    "DIS", "NFLX", "COST", "CRM", "AMD", "INTC", "QCOM", "SPY", "QQQ",
}


class NewsCollector:
    """Fetches financial news from multiple sources."""

    def __init__(self, redis: RedisManager) -> None:
        self.redis = redis
        self.settings = get_settings()

    async def fetch_from_newsapi(
        self,
        query: str = "stock market finance",
        page_size: int = 20,
    ) -> list[dict[str, Any]]:
        """Fetch articles from NewsAPI."""
        import httpx

        api_key = self.settings.news_api_key
        if not api_key:
            logger.warning("NewsAPI key not configured")
            return []

        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": api_key,
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, params=params, timeout=15.0)
                resp.raise_for_status()
                data = resp.json()

            articles = []
            for article in data.get("articles", []):
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "content": article.get("content", ""),
                    "url": article.get("url", ""),
                    "source": article.get("source", {}).get("name", ""),
                    "published_at": article.get("publishedAt", ""),
                    "image_url": article.get("urlToImage"),
                })

            logger.info("Fetched news articles", count=len(articles))
            return articles

        except Exception as e:
            logger.error("NewsAPI fetch failed", error=str(e))
            return []

    async def fetch_ticker_news(self, ticker: str) -> list[dict[str, Any]]:
        """Fetch news specific to a ticker."""
        return await self.fetch_from_newsapi(query=ticker, page_size=10)

    def extract_tickers(self, text: str) -> list[str]:
        """Extract mentioned stock tickers from text."""
        potential = TICKER_PATTERN.findall(text)
        # Filter to known tickers to reduce false positives
        return [t for t in potential if t in KNOWN_TICKERS]

    async def publish_article(self, article: dict[str, Any]) -> None:
        """Publish article to Redis Stream for processing."""
        await self.redis.client.xadd("stream:news:raw", {
            "title": article.get("title", ""),
            "url": article.get("url", ""),
            "source": article.get("source", ""),
            "published_at": article.get("published_at", ""),
        })


class SentimentAnalyzer:
    """FinBERT-based financial sentiment analysis."""

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._pipeline = None

    def _load_model(self) -> None:
        """Lazy-load FinBERT model."""
        if self._pipeline is not None:
            return

        try:
            from transformers import pipeline

            self._pipeline = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=-1,  # CPU; change to 0 for GPU
            )
            logger.info("FinBERT model loaded")
        except Exception as e:
            logger.error("Failed to load FinBERT", error=str(e))
            raise

    def analyze(self, text: str) -> dict[str, float]:
        """Analyze sentiment of a single text.
        
        Returns:
            {"positive": 0.85, "negative": 0.10, "neutral": 0.05, "score": 0.75}
            
        Score range: -1 (very negative) to +1 (very positive)
        """
        self._load_model()

        if not self._pipeline:
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34, "score": 0.0}

        # Truncate to model max length
        text = text[:512]

        try:
            results = self._pipeline(text, return_all_scores=True)
            scores = {r["label"]: r["score"] for r in results[0]}

            # Compute composite score: positive - negative
            composite = scores.get("positive", 0) - scores.get("negative", 0)

            return {
                "positive": scores.get("positive", 0),
                "negative": scores.get("negative", 0),
                "neutral": scores.get("neutral", 0),
                "score": composite,
            }
        except Exception as e:
            logger.error("Sentiment analysis failed", error=str(e))
            return {"positive": 0.33, "negative": 0.33, "neutral": 0.34, "score": 0.0}

    def analyze_batch(self, texts: list[str]) -> list[dict[str, float]]:
        """Batch sentiment analysis for efficiency."""
        return [self.analyze(text) for text in texts]


class NewsProcessor:
    """Processes raw news into enriched records with sentiment and ticker tags."""

    def __init__(self, db: AsyncSession, redis: RedisManager) -> None:
        self.db = db
        self.redis = redis
        self.collector = NewsCollector(redis)
        self.sentiment = SentimentAnalyzer()

    async def process_articles(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Full processing pipeline for raw articles."""
        enriched = []

        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"

            # Sentiment analysis
            sentiment = self.sentiment.analyze(text)

            # Ticker extraction
            tickers = self.collector.extract_tickers(text)

            enriched_article = {
                **article,
                "sentiment_positive": sentiment["positive"],
                "sentiment_negative": sentiment["negative"],
                "sentiment_neutral": sentiment["neutral"],
                "sentiment_score": sentiment["score"],
                "mentioned_tickers": tickers,
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            enriched.append(enriched_article)

        logger.info("Processed articles", count=len(enriched))
        return enriched

    async def run_collection_loop(self, interval_seconds: int = 300) -> None:
        """Periodic news collection and processing."""
        logger.info("Starting news collection loop", interval=interval_seconds)

        while True:
            articles = await self.collector.fetch_from_newsapi()
            if articles:
                await self.process_articles(articles)
            await asyncio.sleep(interval_seconds)
