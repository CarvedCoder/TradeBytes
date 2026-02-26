/**
 * Dashboard Page - Central hub with gamification, portfolio summary, 
 * daily challenge, news feed, and AI predictions overview.
 */

import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { useGamificationStore } from '@/stores/gamificationStore';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import {
  TrendingUp,
  TrendingDown,
  Flame,
  Trophy,
  Target,
  ArrowRight,
  Zap,
  Bot,
  Newspaper,
  LineChart,
} from 'lucide-react';

export default function DashboardPage() {
  // Fetch gamification state
  const { data: gamState } = useQuery({
    queryKey: ['gamification-state'],
    queryFn: () => api.get('/gamification/state').then((r) => r.data),
  });

  // Fetch portfolio overview
  const { data: portfolio } = useQuery({
    queryKey: ['portfolio-overview'],
    queryFn: () => api.get('/portfolio/overview').then((r) => r.data),
  });

  // Fetch daily challenge
  const { data: challenge } = useQuery({
    queryKey: ['daily-challenge'],
    queryFn: () => api.get('/challenges/today').then((r) => r.data),
  });

  // Fetch news feed
  const { data: news } = useQuery({
    queryKey: ['news-feed'],
    queryFn: () => api.get('/news/feed?limit=5').then((r) => r.data),
  });

  // Sync gamification state
  const setGamificationState = useGamificationStore((s) => s.setGamificationState);
  useEffect(() => {
    if (gamState) {
      setGamificationState({
        level: gamState.level,
        totalXp: gamState.total_xp,
        xpToNextLevel: gamState.xp_to_next_level,
        currentStreak: gamState.current_streak,
        longestStreak: gamState.longest_streak,
      });
    }
  }, [gamState, setGamificationState]);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-white">Dashboard</h1>

      {/* Top Stats Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Portfolio Value"
          value={formatCurrency(portfolio?.total_value ?? 10000)}
          change={portfolio?.daily_change ?? 0}
          icon={<TrendingUp className="h-5 w-5" />}
        />
        <StatCard
          title="Day Streak"
          value={`${gamState?.current_streak ?? 0} days`}
          subtitle={`Longest: ${gamState?.longest_streak ?? 0}`}
          icon={<Flame className="h-5 w-5 text-warning" />}
        />
        <StatCard
          title="Win Rate"
          value={formatPercent(portfolio?.win_rate ?? 0)}
          subtitle={`${portfolio?.total_trades ?? 0} trades`}
          icon={<Target className="h-5 w-5 text-accent-400" />}
        />
        <StatCard
          title="Leaderboard Rank"
          value={`#${gamState?.leaderboard_rank ?? '--'}`}
          subtitle="Weekly"
          icon={<Trophy className="h-5 w-5 text-warning" />}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Daily Challenge + Quick Actions */}
        <div className="space-y-6 lg:col-span-2">
          {/* Daily Challenge */}
          <div className="card-hover">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-warning" />
                <h2 className="text-lg font-semibold text-white">Daily Challenge</h2>
              </div>
              <span className="badge-primary">{challenge?.xp_reward ?? 50} XP</span>
            </div>
            <p className="mb-4 text-surface-200">{challenge?.description ?? 'Loading...'}</p>
            <Link to="/simulation" className="btn-primary inline-flex items-center gap-2">
              Start Challenge <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Link to="/simulation" className="card-hover flex items-center gap-3 !p-4">
              <div className="rounded-lg bg-primary-600/20 p-2">
                <LineChart className="h-5 w-5 text-primary-300" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Trading Sim</p>
                <p className="text-xs text-surface-200">Practice trading</p>
              </div>
            </Link>
            <Link to="/advisor" className="card-hover flex items-center gap-3 !p-4">
              <div className="rounded-lg bg-accent-500/20 p-2">
                <Bot className="h-5 w-5 text-accent-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">AI Advisor</p>
                <p className="text-xs text-surface-200">Get insights</p>
              </div>
            </Link>
            <Link to="/news" className="card-hover flex items-center gap-3 !p-4">
              <div className="rounded-lg bg-warning/20 p-2">
                <Newspaper className="h-5 w-5 text-warning" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">News Intel</p>
                <p className="text-xs text-surface-200">Market sentiment</p>
              </div>
            </Link>
          </div>
        </div>

        {/* Right: News Feed */}
        <div className="card">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">Latest News</h2>
            <Link to="/news" className="text-xs text-primary-400 hover:underline">
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {(news?.articles ?? []).slice(0, 5).map((article: any, i: number) => (
              <div key={i} className="border-b border-surface-700 pb-3 last:border-0 last:pb-0">
                <p className="text-sm font-medium text-white line-clamp-2">{article.title}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-surface-200">
                  <span>{article.source}</span>
                  <span>•</span>
                  <SentimentBadge score={article.sentiment_score} />
                </div>
              </div>
            ))}
            {!news?.articles?.length && (
              <p className="text-sm text-surface-200">Loading news...</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  change,
  subtitle,
  icon,
}: {
  title: string;
  value: string;
  change?: number;
  subtitle?: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <span className="text-sm text-surface-200">{title}</span>
        {icon}
      </div>
      <p className="mt-2 text-2xl font-bold text-white">{value}</p>
      {change !== undefined && (
        <p
          className={cn(
            'mt-1 text-sm font-medium',
            change >= 0 ? 'text-success' : 'text-danger',
          )}
        >
          {change >= 0 ? <TrendingUp className="mr-1 inline h-3 w-3" /> : <TrendingDown className="mr-1 inline h-3 w-3" />}
          {formatPercent(change)}
        </p>
      )}
      {subtitle && <p className="mt-1 text-xs text-surface-200">{subtitle}</p>}
    </div>
  );
}

function SentimentBadge({ score }: { score: number }) {
  if (score > 0.2) return <span className="badge-success">Bullish</span>;
  if (score < -0.2) return <span className="badge-danger">Bearish</span>;
  return <span className="badge-warning">Neutral</span>;
}
