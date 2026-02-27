/**
 * Simulation Store - Real-time trading simulation state.
 */

import { create } from 'zustand';

export interface CandleData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface TradeEntry {
  id: string;
  side: 'buy' | 'sell';
  quantity: number;
  price: number;
  timestamp: string;
  pnl?: number;
}

export interface SimulationState {
  sessionId: string | null;
  ticker: string;
  status: 'idle' | 'running' | 'paused' | 'completed';
  speed: number;
  currentCandle: CandleData | null;
  candles: CandleData[];
  trades: TradeEntry[];
  balance: number;
  startingCapital: number;
  position: { quantity: number; avgPrice: number } | null;
  aiPrediction: { direction: 'up' | 'down'; confidence: number } | null;
  pnl: number;
  pnlPercent: number;
}

interface SimulationActions {
  setSession: (sessionId: string, ticker: string, startingCapital: number) => void;
  addCandle: (candle: CandleData) => void;
  addTrade: (trade: TradeEntry) => void;
  setStatus: (status: SimulationState['status']) => void;
  setSpeed: (speed: number) => void;
  setAiPrediction: (prediction: SimulationState['aiPrediction']) => void;
  updateBalance: (balance: number) => void;
  updatePosition: (position: SimulationState['position']) => void;
  reset: () => void;
}

const initialState: SimulationState = {
  sessionId: null,
  ticker: 'AAPL',
  status: 'idle',
  speed: 1,
  currentCandle: null,
  candles: [],
  trades: [],
  balance: 10000,
  startingCapital: 10000,
  position: null,
  aiPrediction: null,
  pnl: 0,
  pnlPercent: 0,
};

export const useSimulationStore = create<SimulationState & SimulationActions>()((set) => ({
  ...initialState,

  setSession: (sessionId, ticker, startingCapital) =>
    set({ ...initialState, sessionId, ticker, startingCapital, balance: startingCapital, status: 'running' }),

  addCandle: (candle) =>
    set((state) => ({
      currentCandle: candle,
      candles: [...state.candles, candle],
    })),

  addTrade: (trade) =>
    set((state) => ({
      trades: trade ? [...state.trades, trade] : state.trades,
    })),

  setStatus: (status) => set({ status }),
  setSpeed: (speed) => set({ speed }),
  setAiPrediction: (aiPrediction) => set({ aiPrediction }),
  updateBalance: (balance) =>
    set((state) => ({
      balance,
      pnl: balance - state.startingCapital,
      pnlPercent: (balance - state.startingCapital) / state.startingCapital,
    })),
  updatePosition: (position) => set({ position }),

  reset: () => set(initialState),
}));
