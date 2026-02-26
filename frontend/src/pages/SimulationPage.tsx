/**
 * Trading Simulation Page - Full simulation interface with:
 * - TradingView-style candlestick chart
 * - Real-time candle streaming via WebSocket
 * - Trade execution panel (Buy/Sell)
 * - AI prediction overlay (vs your trades)
 * - PnL tracking and trade history
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import api from '@/lib/api';
import { useSimulationStore } from '@/stores/simulationStore';
import { createSimulationWS, WebSocketClient } from '@/lib/websocket';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import {
  Play,
  Pause,
  Square,
  FastForward,
  TrendingUp,
  TrendingDown,
  Bot,
  Activity,
} from 'lucide-react';

export default function SimulationPage() {
  const store = useSimulationStore();
  const [ticker, setTicker] = useState('AAPL');
  const [startDate, setStartDate] = useState('2023-01-01');
  const [endDate, setEndDate] = useState('2024-01-01');
  const [startingCapital, setStartingCapital] = useState(10000);
  const [tradeQuantity, setTradeQuantity] = useState(10);
  const wsRef = useRef<WebSocketClient | null>(null);

  // Create simulation session
  const createSession = useMutation({
    mutationFn: (data: any) => api.post('/simulation/sessions', data).then((r) => r.data),
    onSuccess: (data) => {
      store.setSession(data.session_id, ticker, startingCapital);
    },
  });

  // Execute trade
  const executeTrade = useMutation({
    mutationFn: (data: { side: 'buy' | 'sell'; quantity: number }) =>
      api.post(`/simulation/sessions/${store.sessionId}/trade`, data).then((r) => r.data),
    onSuccess: (data) => {
      store.addTrade(data.trade);
      store.updateBalance(data.balance);
      store.updatePosition(data.position);
    },
  });

  // WebSocket connection
  useEffect(() => {
    if (!store.sessionId || store.status !== 'running') return;

    const ws = createSimulationWS(store.sessionId, (msg) => {
      switch (msg.type) {
        case 'candle':
          store.addCandle(msg.data as any);
          break;
        case 'ai_prediction':
          store.setAiPrediction(msg.data as any);
          break;
        case 'session_completed':
          store.setStatus('completed');
          break;
      }
    });
    ws.connect();
    wsRef.current = ws;

    return () => ws.disconnect();
  }, [store.sessionId, store.status]);

  const handleStart = () => {
    createSession.mutate({
      ticker,
      start_date: startDate,
      end_date: endDate,
      starting_capital: startingCapital,
      speed: store.speed,
    });
  };

  const handleSpeedChange = (speed: number) => {
    store.setSpeed(speed);
    wsRef.current?.send({ type: 'speed_change', speed });
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-white">Trading Simulation</h1>
        <div className="flex items-center gap-2">
          <span className={cn(
            'badge',
            store.status === 'running' ? 'badge-success' : 
            store.status === 'paused' ? 'badge-warning' :
            store.status === 'completed' ? 'badge-primary' : 'bg-surface-700 text-surface-200'
          )}>
            {store.status.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Setup Panel (when idle) */}
      {store.status === 'idle' && (
        <div className="card space-y-4">
          <h2 className="text-lg font-semibold">Setup Simulation</h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs text-surface-200">Ticker</label>
              <select value={ticker} onChange={(e) => setTicker(e.target.value)} className="input-field">
                {['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA'].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs text-surface-200">Start Date</label>
              <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-surface-200">End Date</label>
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="mb-1 block text-xs text-surface-200">Starting Capital</label>
              <input type="number" value={startingCapital} onChange={(e) => setStartingCapital(+e.target.value)} className="input-field" />
            </div>
          </div>
          <button onClick={handleStart} className="btn-primary flex items-center gap-2">
            <Play className="h-4 w-4" /> Start Simulation
          </button>
        </div>
      )}

      {/* Active Simulation */}
      {store.status !== 'idle' && (
        <>
          {/* Controls Bar */}
          <div className="card flex items-center justify-between !p-3">
            <div className="flex items-center gap-4">
              <span className="text-sm font-bold text-primary-300">{store.ticker}</span>
              {store.currentCandle && (
                <span className="font-mono text-lg text-white">
                  {formatCurrency(store.currentCandle.close)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {/* Speed controls */}
              {[1, 2, 5, 10].map((s) => (
                <button
                  key={s}
                  onClick={() => handleSpeedChange(s)}
                  className={cn(
                    'rounded px-2 py-1 text-xs font-medium transition-colors',
                    store.speed === s ? 'bg-primary-600 text-white' : 'bg-surface-800 text-surface-200'
                  )}
                >
                  {s}x
                </button>
              ))}
              <button
                onClick={() => {
                  store.setStatus(store.status === 'running' ? 'paused' : 'running');
                  wsRef.current?.send({ type: store.status === 'running' ? 'pause' : 'resume' });
                }}
                className="btn-secondary !px-3 !py-1"
              >
                {store.status === 'running' ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
              </button>
              <button onClick={() => { store.setStatus('completed'); wsRef.current?.disconnect(); }} className="btn-danger !px-3 !py-1">
                <Square className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
            {/* Chart Area (placeholder) */}
            <div className="card lg:col-span-3">
              <div className="flex h-[400px] items-center justify-center rounded-lg border border-dashed border-surface-700">
                <div className="text-center text-surface-200">
                  <Activity className="mx-auto mb-2 h-8 w-8" />
                  <p className="text-sm">Candlestick chart renders here</p>
                  <p className="text-xs">Using lightweight-charts library</p>
                  <p className="mt-2 text-xs">{store.candles.length} candles loaded</p>
                </div>
              </div>
            </div>

            {/* Trade Panel */}
            <div className="space-y-4">
              {/* PnL Card */}
              <div className="card">
                <p className="text-xs text-surface-200">Unrealized P&L</p>
                <p className={cn('text-2xl font-bold', store.pnl >= 0 ? 'text-success' : 'text-danger')}>
                  {formatCurrency(store.pnl)}
                </p>
                <p className={cn('text-sm', store.pnl >= 0 ? 'text-success' : 'text-danger')}>
                  {formatPercent(store.pnlPercent)}
                </p>
              </div>

              {/* AI Prediction */}
              {store.aiPrediction && (
                <div className="card border-primary-500/30">
                  <div className="mb-1 flex items-center gap-2 text-xs text-primary-300">
                    <Bot className="h-3 w-3" /> AI Prediction
                  </div>
                  <div className="flex items-center gap-2">
                    {store.aiPrediction.direction === 'up' ? (
                      <TrendingUp className="h-5 w-5 text-success" />
                    ) : (
                      <TrendingDown className="h-5 w-5 text-danger" />
                    )}
                    <span className="text-lg font-bold text-white">
                      {(store.aiPrediction.confidence * 100).toFixed(0)}%
                    </span>
                    <span className="text-sm text-surface-200">
                      {store.aiPrediction.direction === 'up' ? 'Bullish' : 'Bearish'}
                    </span>
                  </div>
                </div>
              )}

              {/* Trade Execution */}
              <div className="card space-y-3">
                <div>
                  <label className="mb-1 block text-xs text-surface-200">Quantity</label>
                  <input
                    type="number"
                    value={tradeQuantity}
                    onChange={(e) => setTradeQuantity(+e.target.value)}
                    className="input-field"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => executeTrade.mutate({ side: 'buy', quantity: tradeQuantity })}
                    className="btn-success w-full py-3 font-bold"
                    disabled={store.status !== 'running'}
                  >
                    BUY
                  </button>
                  <button
                    onClick={() => executeTrade.mutate({ side: 'sell', quantity: tradeQuantity })}
                    className="btn-danger w-full py-3 font-bold"
                    disabled={store.status !== 'running'}
                  >
                    SELL
                  </button>
                </div>
              </div>

              {/* Position Info */}
              {store.position && (
                <div className="card">
                  <p className="text-xs text-surface-200">Current Position</p>
                  <p className="text-sm font-medium text-white">
                    {store.position.quantity} shares @ {formatCurrency(store.position.avgPrice)}
                  </p>
                </div>
              )}

              {/* Balance */}
              <div className="card">
                <p className="text-xs text-surface-200">Cash Balance</p>
                <p className="text-lg font-bold text-white">{formatCurrency(store.balance)}</p>
              </div>
            </div>
          </div>

          {/* Trade History */}
          {store.trades.length > 0 && (
            <div className="card">
              <h3 className="mb-3 text-sm font-semibold text-white">Trade History</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-surface-700 text-left text-xs text-surface-200">
                      <th className="pb-2">Side</th>
                      <th className="pb-2">Qty</th>
                      <th className="pb-2">Price</th>
                      <th className="pb-2">P&L</th>
                      <th className="pb-2">Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {store.trades.map((trade) => (
                      <tr key={trade.id} className="border-b border-surface-800">
                        <td className={cn('py-2', trade.side === 'buy' ? 'text-success' : 'text-danger')}>
                          {trade.side.toUpperCase()}
                        </td>
                        <td className="py-2 text-white">{trade.quantity}</td>
                        <td className="py-2 text-white">{formatCurrency(trade.price)}</td>
                        <td className={cn('py-2', (trade.pnl ?? 0) >= 0 ? 'text-success' : 'text-danger')}>
                          {trade.pnl !== undefined ? formatCurrency(trade.pnl) : '-'}
                        </td>
                        <td className="py-2 text-surface-200">{trade.timestamp}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
