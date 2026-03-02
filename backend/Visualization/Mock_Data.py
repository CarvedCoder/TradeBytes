"""
Mock data generator for demo — replace with TimescaleDB queries in production.
Generates realistic OHLCV, sentiment, regime, portfolio, and trade data.
"""
import math, random
from datetime import datetime, timedelta
from typing import List
from models.schemas import *

random.seed(42)

def _gbm_prices(n: int, s0: float = 450.0, mu: float = 0.0003, sigma: float = 0.015) -> List[float]:
    """Geometric Brownian Motion price series"""
    prices = [s0]
    for _ in range(n - 1):
        dt = 1
        shock = random.gauss(0, 1)
        ret = math.exp((mu - 0.5 * sigma**2) * dt + sigma * math.sqrt(dt) * shock)
        prices.append(round(prices[-1] * ret, 2))
    return prices

def _timestamps(n: int, interval_min: int = 60, base: datetime = None) -> List[str]:
    base = base or datetime(2024, 1, 2, 9, 30)
    return [(base + timedelta(minutes=i * interval_min)).isoformat() for i in range(n)]

# ─── MARKET / CANDLES ───────────────────────────────────────────────────────
def get_timeseries(ticker: str, n: int = 120) -> TimeseriesResponse:
    closes = _gbm_prices(n, s0=450.0)
    timestamps = _timestamps(n, 60)
    candles = []
    for i, (ts, close) in enumerate(zip(timestamps, closes)):
        spread = close * 0.008
        open_  = closes[i-1] if i > 0 else close * 0.999
        candles.append(OHLCV(
            timestamp=ts,
            open=round(open_, 2),
            high=round(close + abs(random.gauss(0, spread)), 2),
            low=round(close - abs(random.gauss(0, spread)), 2),
            close=close,
            volume=random.randint(800_000, 4_000_000)
        ))
    return TimeseriesResponse(ticker=ticker, interval="1h", candles=candles)

# ─── SENTIMENT ──────────────────────────────────────────────────────────────
def get_sentiment(ticker: str, n: int = 120) -> SentimentResponse:
    timestamps = _timestamps(n, 60)
    base_score = 0.0
    points = []
    for ts in timestamps:
        base_score += random.gauss(0, 0.05)
        base_score = max(-1, min(1, base_score))
        score = round(base_score + random.gauss(0, 0.1), 3)
        score = max(-1.0, min(1.0, score))
        label = "positive" if score > 0.15 else ("negative" if score < -0.15 else "neutral")
        points.append(SentimentPoint(
            timestamp=ts, score=score, label=label,
            article_count=random.randint(2, 18)
        ))
    return SentimentResponse(ticker=ticker, data=points)

# ─── NEWS EVENTS ─────────────────────────────────────────────────────────────
HEADLINES = [
    ("Fed signals pause in rate hikes", 0.72),
    ("Earnings beat expectations by 12%", 0.85),
    ("CEO departure announcement", -0.68),
    ("Product recall issued for flagship device", -0.55),
    ("Strategic acquisition of AI startup", 0.61),
    ("Regulatory probe initiated by SEC", -0.74),
    ("Record quarterly revenue reported", 0.88),
    ("Supply chain disruptions persist", -0.42),
    ("New partnership with major cloud provider", 0.65),
    ("Missed revenue guidance by 8%", -0.71),
]

def get_events(ticker: str) -> EventsResponse:
    timestamps = _timestamps(120, 60)
    chosen_idxs = sorted(random.sample(range(5, 115), 8))
    closes = _gbm_prices(120)
    events = []
    for i, idx in enumerate(chosen_idxs):
        headline, base_sent = HEADLINES[i % len(HEADLINES)]
        price_b = closes[idx - 1]
        price_a = closes[min(idx + 3, 119)]
        abnormal = round((price_a - price_b) / price_b * 100, 3)
        events.append(NewsEvent(
            id=f"evt_{i}",
            timestamp=timestamps[idx],
            headline=headline,
            source=random.choice(["Reuters", "Bloomberg", "WSJ", "FT", "CNBC"]),
            sentiment_score=round(base_sent + random.gauss(0, 0.1), 3),
            price_before=round(price_b, 2),
            price_after=round(price_a, 2),
            abnormal_return=abnormal
        ))
    return EventsResponse(ticker=ticker, events=events)

# ─── PORTFOLIO METRICS ───────────────────────────────────────────────────────
def get_portfolio_metrics(portfolio_id: str) -> PortfolioMetricsResponse:
    return PortfolioMetricsResponse(
        portfolio_id=portfolio_id,
        metrics=RiskMetrics(
            volatility_ann=18.4, beta=0.87, max_drawdown=-12.3,
            diversification_ratio=0.73, sharpe_ratio=1.42,
            sortino_ratio=1.89, var_95=-2.1, cvar_95=-3.4
        ),
        allocation=[
            AllocationItem(asset="AAPL",  weight=22.0, value=27360, sector="Technology"),
            AllocationItem(asset="MSFT",  weight=18.5, value=23030, sector="Technology"),
            AllocationItem(asset="NVDA",  weight=15.0, value=18660, sector="Technology"),
            AllocationItem(asset="JPM",   weight=10.0, value=12440, sector="Financials"),
            AllocationItem(asset="SPY",   weight=12.0, value=14930, sector="ETF"),
            AllocationItem(asset="BND",   weight=8.0,  value=9950,  sector="Bonds"),
            AllocationItem(asset="AMZN",  weight=9.5,  value=11820, sector="Consumer"),
            AllocationItem(asset="CASH",  weight=5.0,  value=6224,  sector="Cash"),
        ]
    )

def get_equity_curve(portfolio_id: str, n: int = 252) -> EquityCurveResponse:
    base = datetime(2024, 1, 2)
    portfolio_vals = _gbm_prices(n, s0=100_000, mu=0.0004, sigma=0.012)
    benchmark_vals = _gbm_prices(n, s0=100_000, mu=0.00035, sigma=0.01)
    peak = portfolio_vals[0]
    data = []
    for i in range(n):
        date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
        peak = max(peak, portfolio_vals[i])
        dd = round((portfolio_vals[i] - peak) / peak * 100, 3)
        data.append(EquityPoint(
            date=date,
            portfolio_value=round(portfolio_vals[i], 2),
            benchmark_value=round(benchmark_vals[i], 2),
            drawdown_pct=dd
        ))
    return EquityCurveResponse(portfolio_id=portfolio_id, data=data)

def get_correlation_matrix() -> CorrelationMatrix:
    assets = ["AAPL", "MSFT", "NVDA", "JPM", "SPY", "BND", "AMZN", "GLD"]
    n = len(assets)
    # Realistic correlation structure
    base = [
        [1.00, 0.82, 0.71, 0.41, 0.78, -0.18, 0.65, -0.12],
        [0.82, 1.00, 0.68, 0.38, 0.75, -0.21, 0.70, -0.09],
        [0.71, 0.68, 1.00, 0.29, 0.62, -0.14, 0.58, -0.05],
        [0.41, 0.38, 0.29, 1.00, 0.55, 0.12,  0.36, 0.08],
        [0.78, 0.75, 0.62, 0.55, 1.00, 0.05,  0.72, -0.02],
        [-0.18,-0.21,-0.14, 0.12, 0.05, 1.00, -0.15, 0.42],
        [0.65, 0.70, 0.58, 0.36, 0.72, -0.15, 1.00, -0.08],
        [-0.12,-0.09,-0.05, 0.08,-0.02, 0.42, -0.08, 1.00],
    ]
    return CorrelationMatrix(assets=assets, matrix=base, period_days=90)

# ─── REGIME ──────────────────────────────────────────────────────────────────
def get_regime(ticker: str, n: int = 120) -> RegimeResponse:
    closes = _gbm_prices(n)
    timestamps = _timestamps(n, 60)
    candles = []
    for i, (ts, close) in enumerate(zip(timestamps, closes)):
        spread = close * 0.008
        open_ = closes[i-1] if i > 0 else close * 0.999
        candles.append(OHLCV(timestamp=ts, open=round(open_,2),
            high=round(close+abs(random.gauss(0,spread)),2),
            low=round(close-abs(random.gauss(0,spread)),2),
            close=close, volume=random.randint(800000,4000000)))

    # Define regime segments (simulating HMM output)
    regime_schedule = [
        (0,  30,  RegimeType.TRENDING,    0.91),
        (30, 55,  RegimeType.VOLATILE,    0.88),
        (55, 80,  RegimeType.MEAN_REVERT, 0.76),
        (80, 95,  RegimeType.TRENDING,    0.83),
        (95, 120, RegimeType.VOLATILE,    0.79),
    ]
    segments = [RegimeSegment(
        start=timestamps[s], end=timestamps[min(e-1,n-1)],
        regime=r, confidence=c
    ) for s, e, r, c in regime_schedule]

    # Regime probabilities per bar
    probs = []
    for i, ts in enumerate(timestamps):
        seg = next((seg for s,e,r,c in regime_schedule if s <= i < e), None)
        s, e, r, c = next((x for x in regime_schedule if x[0] <= i < x[1]), regime_schedule[-1])
        p_t = c if r == RegimeType.TRENDING    else round(random.uniform(0.05, 0.25), 3)
        p_v = c if r == RegimeType.VOLATILE    else round(random.uniform(0.05, 0.25), 3)
        p_m = c if r == RegimeType.MEAN_REVERT else round(1 - p_t - p_v, 3)
        probs.append(RegimeProbPoint(timestamp=ts, p_trending=p_t,
            p_volatile=p_v, p_mean_revert=max(0,p_m), dominant=r))

    transitions = [{"from": regime_schedule[i][2], "to": regime_schedule[i+1][2],
                    "timestamp": timestamps[regime_schedule[i+1][0]]}
                   for i in range(len(regime_schedule)-1)]

    return RegimeResponse(ticker=ticker, price_data=candles,
                          segments=segments, probabilities=probs, transitions=transitions)

# ─── TRADES ──────────────────────────────────────────────────────────────────
AI_SIGNALS = ["Strong buy signal", "Momentum breakout", "Mean reversion entry",
              "Regime shift detected", "Risk-off signal", "Volume surge signal"]

def get_trade_session(session_id: str) -> TradeSessionResponse:
    ticker = "NVDA"
    n = 80
    closes = _gbm_prices(n, s0=580.0, sigma=0.018)
    timestamps = _timestamps(n, 30, base=datetime(2024, 6, 3, 9, 30))
    candles = []
    for i, (ts, close) in enumerate(zip(timestamps, closes)):
        spread = close * 0.01
        open_ = closes[i-1] if i > 0 else close
        candles.append(OHLCV(timestamp=ts, open=round(open_,2),
            high=round(close+abs(random.gauss(0,spread)),2),
            low=round(close-abs(random.gauss(0,spread)),2),
            close=close, volume=random.randint(1_000_000, 8_000_000)))

    trade_idxs = [8, 22, 35, 50, 65]
    actions = [TradeAction.BUY, TradeAction.SELL, TradeAction.BUY, TradeAction.SELL, TradeAction.BUY]
    mistakes = [False, False, True, False, False]
    mistake_reasons = [None, None, "Sold too early — missed 8% continuation", None, None]
    pnls = [None, round((closes[22]-closes[8])*10, 2), None,
            round((closes[50]-closes[35])*10, 2), None]

    trades = [Trade(
        id=f"trd_{i}", timestamp=timestamps[idx], action=actions[i],
        ticker=ticker, price=closes[idx], quantity=10,
        pnl=pnls[i], ai_signal=random.choice(AI_SIGNALS),
        is_mistake=mistakes[i], mistake_reason=mistake_reasons[i]
    ) for i, idx in enumerate(trade_idxs)]

    cum_pnl = 0.0
    pnl_timeline = []
    trade_map = {t.timestamp: t.pnl for t in trades if t.pnl is not None}
    for ts in timestamps:
        tp = trade_map.get(ts)
        if tp: cum_pnl += tp
        pnl_timeline.append(PnLPoint(timestamp=ts, cumulative_pnl=round(cum_pnl,2),
                                      trade_pnl=tp))

    total = sum(t.pnl for t in trades if t.pnl)
    return TradeSessionResponse(
        session_id=session_id, ticker=ticker, candles=candles,
        trades=trades, pnl_timeline=pnl_timeline,
        session_summary={"total_trades": 5, "winning_trades": 2, "total_pnl": round(total,2),
                         "win_rate": 0.67, "avg_pnl_per_trade": round(total/2,2)}
    )