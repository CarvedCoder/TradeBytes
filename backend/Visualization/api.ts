// services/api.ts — Production API layer with error handling + caching

import axios, { AxiosInstance } from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: add auth token if available
api.interceptors.request.use(config => {
  const token = localStorage.getItem('finai_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor: normalize errors
api.interceptors.response.use(
  res => res.data,
  err => {
    const msg = err.response?.data?.detail || err.message || 'Unknown error';
    console.error(`[FinAI API Error] ${err.config?.url}: ${msg}`);
    return Promise.reject(new Error(msg));
  }
);

// ── Typed API calls ────────────────────────────────────────────────────────

export const marketApi = {
  timeseries: (ticker: string, n=120) =>
    api.get(`/market/${ticker}/timeseries?n=${n}`),
  sentiment: (ticker: string) =>
    api.get(`/market/${ticker}/sentiment`),
  events: (ticker: string) =>
    api.get(`/market/${ticker}/events`),
  correlationMatrix: (period=90) =>
    api.get(`/market/correlation-matrix?period_days=${period}`),
};

export const portfolioApi = {
  metrics: (id='default') =>
    api.get(`/portfolio/metrics?portfolio_id=${id}`),
  equityCurve: (id='default', days=252) =>
    api.get(`/portfolio/equity-curve?portfolio_id=${id}&days=${days}`),
  correlation: (period=90) =>
    api.get(`/portfolio/correlation?period_days=${period}`),
};

export const regimeApi = {
  regime: (ticker: string) =>
    api.get(`/regime/${ticker}`),
};

export const tradesApi = {
  session: (sessionId: string) =>
    api.get(`/trades/session/${sessionId}`),
};

// ── React Query hooks (production pattern) ───────────────────────────────
/*
import { useQuery } from '@tanstack/react-query';

export function useMarketTimeseries(ticker: string) {
  return useQuery({
    queryKey: ['timeseries', ticker],
    queryFn: () => marketApi.timeseries(ticker),
    staleTime: 60_000,       // 1 min cache
    gcTime:    300_000,      // 5 min in memory
    retry: 2,
  });
}

export function usePortfolioMetrics() {
  return useQuery({
    queryKey: ['portfolio', 'metrics'],
    queryFn: portfolioApi.metrics,
    staleTime: 120_000,
  });
}

export function useRegime(ticker: string) {
  return useQuery({
    queryKey: ['regime', ticker],
    queryFn: () => regimeApi.regime(ticker),
    staleTime: 300_000,  // regimes change slowly
  });
}
*/