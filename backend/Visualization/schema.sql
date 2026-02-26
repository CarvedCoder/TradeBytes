-- FinAI TimescaleDB Schema + Optimized Queries
-- Production-grade design for financial time series

-- ─── HYPERTABLES ────────────────────────────────────────────────────────────

CREATE TABLE market_data (
    ts          TIMESTAMPTZ     NOT NULL,
    ticker      VARCHAR(10)     NOT NULL,
    open        NUMERIC(12,4),
    high        NUMERIC(12,4),
    low         NUMERIC(12,4),
    close       NUMERIC(12,4),
    volume      BIGINT
);
SELECT create_hypertable('market_data', 'ts', chunk_time_interval => INTERVAL '7 days');
CREATE INDEX ON market_data (ticker, ts DESC);

CREATE TABLE news_sentiment (
    ts              TIMESTAMPTZ NOT NULL,
    ticker          VARCHAR(10),
    headline        TEXT,
    source          VARCHAR(50),
    sentiment_score NUMERIC(5,4),
    article_count   INT
);
SELECT create_hypertable('news_sentiment', 'ts', chunk_time_interval => INTERVAL '7 days');

CREATE TABLE regime_labels (
    ts          TIMESTAMPTZ NOT NULL,
    ticker      VARCHAR(10) NOT NULL,
    regime      VARCHAR(20),   -- 'trending' | 'volatile' | 'mean_reverting'
    p_trending  NUMERIC(5,4),
    p_volatile  NUMERIC(5,4),
    p_mean_rev  NUMERIC(5,4),
    confidence  NUMERIC(5,4)
);
SELECT create_hypertable('regime_labels', 'ts', chunk_time_interval => INTERVAL '30 days');

CREATE TABLE portfolio_snapshots (
    ts              TIMESTAMPTZ NOT NULL,
    portfolio_id    VARCHAR(50),
    total_value     NUMERIC(15,2),
    benchmark_value NUMERIC(15,2),
    drawdown_pct    NUMERIC(8,4)
);
SELECT create_hypertable('portfolio_snapshots', 'ts');

CREATE TABLE trades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      VARCHAR(50),
    ts              TIMESTAMPTZ NOT NULL,
    ticker          VARCHAR(10),
    action          VARCHAR(4),  -- BUY | SELL
    price           NUMERIC(12,4),
    quantity        INT,
    pnl             NUMERIC(12,2),
    ai_signal       TEXT,
    is_mistake      BOOLEAN DEFAULT FALSE,
    mistake_reason  TEXT
);

-- ─── OPTIMIZED QUERIES ──────────────────────────────────────────────────────

-- Candle aggregation (1-hour buckets) — O(log n) via TimescaleDB
SELECT
    time_bucket('1 hour', ts) AS bucket,
    first(open,  ts)          AS open,
    max(high)                 AS high,
    min(low)                  AS low,
    last(close,  ts)          AS close,
    sum(volume)               AS volume
FROM market_data
WHERE ticker = $1
  AND ts >= NOW() - INTERVAL '30 days'
GROUP BY bucket
ORDER BY bucket DESC;

-- Time-aligned sentiment JOIN (key: same time_bucket)
SELECT
    m.bucket,
    m.close,
    s.avg_score AS sentiment,
    s.article_count
FROM (
    SELECT time_bucket('1h', ts) AS bucket, last(close, ts) AS close
    FROM market_data WHERE ticker=$1 AND ts >= NOW()-INTERVAL '30d'
    GROUP BY bucket
) m
LEFT JOIN (
    SELECT time_bucket('1h', ts) AS bucket,
           avg(sentiment_score) AS avg_score,
           count(*) AS article_count
    FROM news_sentiment WHERE ticker=$1 AND ts >= NOW()-INTERVAL '30d'
    GROUP BY bucket
) s USING (bucket)
ORDER BY m.bucket;

-- Rolling correlation (computed in Python, cached in Redis)
-- Python:
-- df = pd.DataFrame(prices_dict)
-- corr = df.rolling(window=90).corr().iloc[-len(assets):]
-- redis.setex(f"corr:{portfolio_id}", 3600, corr.to_json())

-- Regime transitions detection
WITH lagged AS (
    SELECT ts, ticker, regime,
           LAG(regime) OVER (PARTITION BY ticker ORDER BY ts) AS prev_regime
    FROM regime_labels WHERE ticker=$1
)
SELECT ts, prev_regime AS from_regime, regime AS to_regime
FROM lagged WHERE regime != prev_regime AND prev_regime IS NOT NULL;

-- ─── CONTINUOUS AGGREGATES (pre-materialized for dashboards) ───────────────

CREATE MATERIALIZED VIEW candles_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', ts) AS bucket,
    ticker,
    first(open, ts) AS open, max(high) AS high,
    min(low) AS low, last(close, ts) AS close,
    sum(volume) AS volume
FROM market_data
GROUP BY bucket, ticker;

-- Refresh policy
SELECT add_continuous_aggregate_policy('candles_1d',
    start_offset => INTERVAL '7 days',
    end_offset   => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour');