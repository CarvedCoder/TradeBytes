/**
 * Portfolio Page - Portfolio analytics with allocation, risk metrics, and AI suggestions.
 */

import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import { PieChart, Shield, TrendingDown, Bot, Briefcase } from 'lucide-react';

export default function PortfolioPage() {
  const { data: overview } = useQuery({
    queryKey: ['portfolio-overview'],
    queryFn: () => api.get('/portfolio/overview').then((r) => r.data),
  });

  const { data: allocation } = useQuery({
    queryKey: ['portfolio-allocation'],
    queryFn: () => api.get('/portfolio/allocation').then((r) => r.data),
  });

  const { data: riskMetrics } = useQuery({
    queryKey: ['portfolio-risk'],
    queryFn: () => api.get('/portfolio/risk-metrics').then((r) => r.data),
  });

  const { data: aiSuggestions } = useQuery({
    queryKey: ['portfolio-ai-suggestions'],
    queryFn: () => api.get('/portfolio/ai-suggestions').then((r) => r.data),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Portfolio</h1>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="card">
          <div className="flex items-center gap-2 text-sm text-surface-200">
            <Briefcase className="h-4 w-4" /> Total Value
          </div>
          <p className="mt-1 text-2xl font-bold text-white">
            {formatCurrency(overview?.total_value ?? 0)}
          </p>
          <p className={cn('text-sm', (overview?.daily_change ?? 0) >= 0 ? 'text-success' : 'text-danger')}>
            {formatPercent(overview?.daily_change ?? 0)} today
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 text-sm text-surface-200">
            <PieChart className="h-4 w-4" /> Positions
          </div>
          <p className="mt-1 text-2xl font-bold text-white">{overview?.position_count ?? 0}</p>
          <p className="text-sm text-surface-200">{overview?.total_trades ?? 0} total trades</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 text-sm text-surface-200">
            <Shield className="h-4 w-4" /> Sharpe Ratio
          </div>
          <p className="mt-1 text-2xl font-bold text-white">
            {(riskMetrics?.sharpe_ratio ?? 0).toFixed(2)}
          </p>
          <p className="text-sm text-surface-200">Risk-adjusted return</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 text-sm text-surface-200">
            <TrendingDown className="h-4 w-4" /> Max Drawdown
          </div>
          <p className="mt-1 text-2xl font-bold text-danger">
            {formatPercent(riskMetrics?.max_drawdown ?? 0)}
          </p>
          <p className="text-sm text-surface-200">Worst peak-to-trough</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Allocation */}
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-white">Allocation</h2>
          <div className="space-y-2">
            {(allocation?.holdings ?? []).map((h: any) => (
              <div key={h.ticker} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="h-3 w-3 rounded-full bg-primary-500" />
                  <span className="text-sm font-medium text-white">{h.ticker}</span>
                </div>
                <div className="text-right">
                  <span className="text-sm text-white">{formatCurrency(h.value)}</span>
                  <span className="ml-2 text-xs text-surface-200">{(h.weight * 100).toFixed(1)}%</span>
                </div>
              </div>
            ))}
            {!allocation?.holdings?.length && (
              <p className="text-sm text-surface-200">No positions yet. Start trading!</p>
            )}
          </div>
        </div>

        {/* Risk Metrics */}
        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-white">Risk Metrics</h2>
          <div className="space-y-3">
            {[
              { label: 'Volatility (Ann.)', value: formatPercent(riskMetrics?.volatility ?? 0) },
              { label: 'Beta', value: (riskMetrics?.beta ?? 0).toFixed(2) },
              { label: 'Value at Risk (95%)', value: formatCurrency(riskMetrics?.var_95 ?? 0) },
              { label: 'Sortino Ratio', value: (riskMetrics?.sortino_ratio ?? 0).toFixed(2) },
              { label: 'Calmar Ratio', value: (riskMetrics?.calmar_ratio ?? 0).toFixed(2) },
            ].map((metric) => (
              <div key={metric.label} className="flex items-center justify-between border-b border-surface-800 pb-2 last:border-0">
                <span className="text-sm text-surface-200">{metric.label}</span>
                <span className="text-sm font-medium text-white">{metric.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* AI Suggestions */}
      <div className="card">
        <div className="mb-4 flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary-400" />
          <h2 className="text-lg font-semibold text-white">AI Suggestions</h2>
        </div>
        <div className="space-y-3">
          {(aiSuggestions?.suggestions ?? []).map((s: any, i: number) => (
            <div key={i} className="rounded-lg border border-surface-700 bg-surface-800 p-4">
              <div className="mb-1 flex items-center gap-2">
                <span className={cn('badge', s.type === 'buy' ? 'badge-success' : s.type === 'sell' ? 'badge-danger' : 'badge-warning')}>
                  {s.type?.toUpperCase()}
                </span>
                <span className="text-sm font-medium text-white">{s.ticker}</span>
              </div>
              <p className="text-sm text-surface-200">{s.reasoning}</p>
            </div>
          ))}
          {!aiSuggestions?.suggestions?.length && (
            <p className="text-sm text-surface-200">Trade more to receive AI-powered suggestions.</p>
          )}
        </div>
      </div>
    </div>
  );
}
