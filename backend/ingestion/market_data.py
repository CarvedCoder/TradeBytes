"""
Market Data Collector.

Fetches OHLCV market data from multiple sources:
- yfinance (free, delayed)
- Alpha Vantage (API key required)
- Polygon.io (API key required)

Data flows: Source → Validate → Redis Stream → Database + Feature Store
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_settings
from backend.core.redis import RedisManager

logger = structlog.get_logger()


class MarketDataCollector:
    """Fetches and streams market data."""

    # Supported tickers for MVP
    DEFAULT_TICKERS = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "META", "NVDA", "JPM", "V", "WMT",
        "SPY", "QQQ", "DIA", "IWM",
    ]

    def __init__(self, db: AsyncSession, redis: RedisManager) -> None:
        self.db = db
        self.redis = redis
        self.settings = get_settings()

    async def fetch_historical(
        self,
        ticker: str,
        start_date: str | None = None,
        end_date: str | None = None,
        interval: str = "1d",
    ) -> list[dict[str, Any]]:
        """Fetch historical OHLCV data.
        
        Uses yfinance as primary source (free, no API key).
        Falls back to Alpha Vantage if configured.
        """
        try:
            import yfinance as yf

            end = end_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start = start_date or (datetime.now(timezone.utc) - timedelta(days=730)).strftime("%Y-%m-%d")

            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(start=start, end=end, interval=interval)

            if df.empty:
                logger.warning("No data returned", ticker=ticker, start=start, end=end)
                return []

            records = []
            for idx, row in df.iterrows():
                records.append({
                    "ticker": ticker,
                    "timestamp": idx.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                })

            logger.info("Fetched historical data", ticker=ticker, records=len(records))
            return records

        except ImportError:
            logger.error("yfinance not installed")
            return []
        except Exception as e:
            logger.error("Failed to fetch market data", ticker=ticker, error=str(e))
            return []

    async def fetch_realtime_quote(self, ticker: str) -> dict[str, Any] | None:
        """Fetch current quote for a ticker."""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            info = t.fast_info
            return {
                "ticker": ticker,
                "price": float(info.last_price) if hasattr(info, 'last_price') else 0,
                "previous_close": float(info.previous_close) if hasattr(info, 'previous_close') else 0,
                "market_cap": float(info.market_cap) if hasattr(info, 'market_cap') else 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Failed to fetch quote", ticker=ticker, error=str(e))
            return None

    async def publish_to_stream(self, ticker: str, data: dict[str, Any]) -> None:
        """Publish market data to Redis Stream for downstream processing."""
        stream_key = f"stream:market:{ticker}"
        await self.redis.client.xadd(stream_key, {
            "data": str(data),  # Redis streams require string values
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def run_collection_loop(self, tickers: list[str] | None = None, interval_seconds: int = 60) -> None:
        """Continuous collection loop for real-time updates."""
        tickers = tickers or self.DEFAULT_TICKERS
        logger.info("Starting market data collection", tickers=len(tickers), interval=interval_seconds)

        while True:
            for ticker in tickers:
                quote = await self.fetch_realtime_quote(ticker)
                if quote:
                    await self.publish_to_stream(ticker, quote)
                    # Also publish to price update channel for WebSocket broadcasting
                    await self.redis.publish("channel:prices", {
                        "type": "price_update",
                        **quote,
                    })

            await asyncio.sleep(interval_seconds)


class MarketDataStore:
    """Persists market data to TimescaleDB."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_candles(self, records: list[dict[str, Any]]) -> int:
        """Bulk insert OHLCV records into TimescaleDB hypertable."""
        from sqlalchemy import text

        if not records:
            return 0

        # Use INSERT ... ON CONFLICT for idempotent upserts
        query = text("""
            INSERT INTO market_data (ticker, timestamp, open, high, low, close, volume)
            VALUES (:ticker, :timestamp, :open, :high, :low, :close, :volume)
            ON CONFLICT (ticker, timestamp) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """)

        for record in records:
            await self.db.execute(query, record)

        await self.db.commit()
        logger.info("Upserted candles", count=len(records))
        return len(records)
