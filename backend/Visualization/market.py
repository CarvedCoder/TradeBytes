from fastapi import APIRouter, Query
from models.schemas import TimeseriesResponse, SentimentResponse, EventsResponse, CorrelationMatrix
from services.mock_data import get_timeseries, get_sentiment, get_events, get_correlation_matrix

router = APIRouter()

@router.get("/{ticker}/timeseries", response_model=TimeseriesResponse)
async def market_timeseries(ticker: str, n: int = Query(120, ge=10, le=500)):
    """
    OHLCV candles for ticker.
    Production: SELECT time_bucket('1h', ts) ... FROM market_data WHERE ticker=$1
    TimescaleDB: uses hypertable on (ticker, ts) with chunk_time_interval='7 days'
    """
    return get_timeseries(ticker.upper(), n)

@router.get("/{ticker}/sentiment", response_model=SentimentResponse)
async def market_sentiment(ticker: str, n: int = Query(120, ge=10, le=500)):
    """
    Hourly sentiment aggregated from news NLP pipeline.
    Time-aligned to candle timestamps via JOIN on time_bucket.
    """
    return get_sentiment(ticker.upper(), n)

@router.get("/{ticker}/events", response_model=EventsResponse)
async def market_events(ticker: str):
    """
    Discrete news events with abnormal return computation.
    Abnormal return = (P[t+3h] - P[t-1h]) / P[t-1h] - benchmark_return
    """
    return get_events(ticker.upper())

@router.get("/correlation-matrix", response_model=CorrelationMatrix)
async def correlation_matrix(period_days: int = Query(90, ge=30, le=365)):
    """
    Rolling Pearson correlation matrix for portfolio assets.
    Production: computed via pandas rolling(window=period_days).corr() cached in Redis (TTL 1h)
    """
    return get_correlation_matrix()