/**
 * Dashboard Page - Gamified hub with XP/streak/level display, daily challenge,
 * learning paths, leaderboard preview, portfolio snapshot, and AI arena CTA.
 * 
 * All data fetched via existing API endpoints - no backend changes.
 */

import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { useGamificationStore } from '@/stores/gamificationStore';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import {
  TrendingUp,
  TrendingDown,
  ArrowRight,
  Bot,
  Newspaper,
  LineChart,
  Swords,
  BookOpen,
  Briefcase,
} from 'lucide-react';
import { XPBar, StreakCounter, LevelBadge, DailyCard, UnlockCard, LeaderboardPreview } from '@/components/gamification';

// ---------------------------------------------------------------------------
// Motivational messages derived from user data
// ---------------------------------------------------------------------------
function getMotivation(streak: number, level: number): string {
  if (streak >= 30) return 'Unstoppable. Your discipline is paying off.';
  if (streak >= 14) return 'Two weeks strong -- keep this momentum going.';
  if (streak >= 7) return 'Solid week! Consistency builds mastery.';
  if (streak >= 3) return 'Great start -- a few more days to lock in the habit.';
  if (level >= 15) return 'You are becoming an expert. Push further.';
  if (level >= 5) return 'Nice progress! Level up with today\'s challenge.';
  return 'Welcome back. Let\'s make today count.';
}

// ---------------------------------------------------------------------------
// Dashboard Page
// ---------------------------------------------------------------------------
export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);

  // ---- Existing API queries (unchanged) ----
  const { data: gamState } = useQuery({
    queryKey: ['gamification-state'],
    queryFn: () => api.get('/gamification/state').then((r) => r.data),
  });

  const { data: portfolio, isLoading: portfolioLoading } = useQuery({
    queryKey: ['portfolio-overview'],
    queryFn: () => api.get('/portfolio/overview').then((r) => r.data),
  });

  const { data: challenge, isLoading: challengeLoading } = useQuery({
    queryKey: ['daily-challenge'],
    queryFn: () => api.get('/challenges/today').then((r) => r.data),
  });

  const { data: news } = useQuery({
    queryKey: ['news-feed'],
    queryFn: () => api.get('/news/feed?limit=5').then((r) => r.data),
  });

  const { data: leaderboard, isLoading: lbLoading } = useQuery({
    queryKey: ['leaderboard', 'weekly'],
    queryFn: () => api.get('/leaderboard?period=weekly').then((r) => r.data),
  });

  const { data: myRank } = useQuery({
    queryKey: ['my-rank'],
    queryFn: () => api.get('/leaderboard/me').then((r) => r.data),
  });

  const { data: paths } = useQuery({
    queryKey: ['learning-paths'],
    queryFn: () => api.get('/learning/paths').then((r) => r.data),
  });

  // ---- Sync gamification store (unchanged) ----
  const { setGamificationState, recentXpGain } = useGamificationStore();
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

  // ---- Derived values ----
  const level = gamState?.level ?? user?.level ?? 1;
  const totalXp = gamState?.total_xp ?? user?.total_xp ?? 0;
  const xpToNext = gamState?.xp_to_next_level ?? 100;
  const streak = gamState?.current_streak ?? user?.current_streak ?? 0;
  const longestStreak = gamState?.longest_streak ?? 0;
  const motivation = useMemo(() => getMotivation(streak, level), [streak, level]);

  // Map leaderboard entries to preview format
  const lbEntries = useMemo(() => {
    return (leaderboard?.entries ?? []).slice(0, 5).map((e: any) => ({
      user_id: e.user_id,
      display_name: e.display_name ?? 'Trader',
      total_xp: e.total_xp ?? 0,
      current_streak: e.current_streak ?? 0,
      is_current_user: e.user_id === user?.id,
    }));
  }, [leaderboard, user?.id]);

  // Learning path items for unlock cards
  const learningPaths = useMemo(() => {
    return (paths?.paths ?? []).slice(0, 4);
  }, [paths]);

  return (
    <div className="space-y-6">
      {/* ================================================================
          TOP SECTION: Avatar + Level + XP + Streak + Motivation
          ================================================================ */}
      <section className="card-gamified animate-card-enter p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-6">
          {/* Avatar + Level Badge */}
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-600 to-primary-500 text-xl font-bold text-white shadow-lg shadow-primary-500/25">
                {user?.display_name?.charAt(0).toUpperCase() ?? '?'}
              </div>
              <div className="absolute -bottom-1 -right-1">
                <LevelBadge level={level} size="sm" />
              </div>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">
                {user?.display_name ?? 'Trader'}
              </h1>
              <p className="text-sm text-surface-300">{motivation}</p>
            </div>
          </div>

          {/* XP Bar (fills middle) */}
          <div className="flex-1 min-w-0 lg:max-w-md">
            <XPBar
              currentXp={totalXp}
              xpToNextLevel={xpToNext}
              level={level}
              recentXpGain={recentXpGain}
              size="md"
            />
          </div>

          {/* Streak Counter */}
          <StreakCounter
            streak={streak}
            longestStreak={longestStreak}
            variant="full"
          />
        </div>
      </section>

      {/* ================================================================
          MIDDLE SECTION: Daily Challenge + Continue Learning + AI Arena
          ================================================================ */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Daily Challenge Card */}
        <DailyCard
          challenge={challenge}
          isLoading={challengeLoading}
          className="animate-slide-up lg:col-span-2"
        />

        {/* AI Trading Arena CTA */}
        <Link
          to="/simulation"
          className="card-gamified group flex flex-col justify-between p-5 transition-all animate-slide-up-delay hover:border-primary-500/40"
        >
          <div>
            <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-xl bg-primary-500/15">
              <Swords className="h-5 w-5 text-primary-400" />
            </div>
            <h3 className="text-sm font-semibold text-white">Enter AI Trading Arena</h3>
            <p className="mt-1 text-xs text-surface-300">
              Test your skills against the AI. Beat its predictions to earn bonus XP.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1 text-xs font-medium text-primary-400 transition-colors group-hover:text-primary-300">
            Start session <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-1" />
          </div>
        </Link>
      </section>

      {/* Continue Learning Path */}
      {learningPaths.length > 0 && (
        <section className="animate-slide-up-delay">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-accent-400" />
              <h2 className="text-sm font-semibold text-white">Learning Paths</h2>
            </div>
            <Link to="/learning" className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {learningPaths.map((p: any) => (
              <UnlockCard
                key={p.slug}
                title={p.title}
                description={p.description}
                xpReward={p.xp_reward}
                difficulty={p.difficulty}
                locked={!p.enrolled && p.requires_level ? level < p.requires_level : false}
                completed={p.completed_modules === p.total_modules && p.total_modules > 0}
                progress={p.total_modules > 0 ? (p.completed_modules / p.total_modules) * 100 : 0}
                lockReason={p.requires_level ? `Requires Level ${p.requires_level}` : undefined}
                href="/learning"
              />
            ))}
          </div>
        </section>
      )}

      {/* ================================================================
          BOTTOM SECTION: Leaderboard + Portfolio + News + Quick Links
          ================================================================ */}
      <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Leaderboard Preview */}
        <LeaderboardPreview
          entries={lbEntries}
          myRank={myRank?.rank}
          isLoading={lbLoading}
          className="animate-slide-up-delay-2"
        />

        {/* Portfolio Snapshot */}
        <div className="card-gamified animate-slide-up-delay-2 p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Briefcase className="h-4 w-4 text-accent-400" />
              <h3 className="text-sm font-semibold text-white">Portfolio</h3>
            </div>
            <Link to="/portfolio" className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300">
              Details <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-4">
            <div>
              <p className="text-xs text-surface-400">Total Value</p>
              <p className="text-2xl font-bold text-white">
                {portfolioLoading ? (
                  <span className="inline-block h-7 w-28 animate-pulse rounded bg-surface-800" />
                ) : (
                  formatCurrency(portfolio?.total_value ?? 10000)
                )}
              </p>
              {portfolio?.daily_change !== undefined && (
                <div className={cn(
                  'mt-1 flex items-center gap-1 text-sm font-medium',
                  portfolio.daily_change >= 0 ? 'text-success' : 'text-danger',
                )}>
                  {portfolio.daily_change >= 0 ? (
                    <TrendingUp className="h-3.5 w-3.5" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5" />
                  )}
                  {formatPercent(portfolio.daily_change)} today
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-surface-800/50 p-2.5">
                <p className="text-[10px] text-surface-400">Win Rate</p>
                <p className="text-sm font-bold text-white">
                  {portfolio?.win_rate !== undefined
                    ? formatPercent(portfolio.win_rate)
                    : '--'}
                </p>
              </div>
              <div className="rounded-lg bg-surface-800/50 p-2.5">
                <p className="text-[10px] text-surface-400">Trades</p>
                <p className="text-sm font-bold text-white">
                  {portfolio?.total_trades ?? 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* News + Quick Actions */}
        <div className="space-y-4 animate-slide-up-delay-2">
          {/* News Feed Mini */}
          <div className="card-gamified p-5">
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Newspaper className="h-4 w-4 text-warning" />
                <h3 className="text-sm font-semibold text-white">Latest News</h3>
              </div>
              <Link to="/news" className="text-xs text-primary-400 hover:text-primary-300">
                All
              </Link>
            </div>
            <div className="space-y-2.5">
              {(news?.articles ?? []).slice(0, 3).map((article: any, i: number) => (
                <div key={i} className="border-b border-surface-800 pb-2.5 last:border-0 last:pb-0">
                  <p className="text-xs font-medium text-white line-clamp-2">{article.title}</p>
                  <div className="mt-0.5 flex items-center gap-2 text-[10px] text-surface-400">
                    <span>{article.source}</span>
                    <SentimentDot score={article.sentiment_score} />
                  </div>
                </div>
              ))}
              {!news?.articles?.length && (
                <p className="text-xs text-surface-400">Loading news...</p>
              )}
            </div>
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-2 gap-2">
            <Link
              to="/advisor"
              className="card-gamified flex items-center gap-2.5 !p-3 transition-all hover:border-primary-500/30"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-500/15">
                <Bot className="h-4 w-4 text-primary-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-white">AI Advisor</p>
                <p className="text-[10px] text-surface-400">Get insights</p>
              </div>
            </Link>
            <Link
              to="/simulation"
              className="card-gamified flex items-center gap-2.5 !p-3 transition-all hover:border-primary-500/30"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-400/15">
                <LineChart className="h-4 w-4 text-accent-400" />
              </div>
              <div>
                <p className="text-xs font-medium text-white">Trade Sim</p>
                <p className="text-[10px] text-surface-400">Practice now</p>
              </div>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Small helper: coloured sentiment dot
// ---------------------------------------------------------------------------
function SentimentDot({ score }: { score: number }) {
  if (score > 0.2) return <span className="inline-flex items-center gap-0.5 text-success"><span className="h-1.5 w-1.5 rounded-full bg-success" /> Bullish</span>;
  if (score < -0.2) return <span className="inline-flex items-center gap-0.5 text-danger"><span className="h-1.5 w-1.5 rounded-full bg-danger" /> Bearish</span>;
  return <span className="inline-flex items-center gap-0.5 text-surface-400"><span className="h-1.5 w-1.5 rounded-full bg-surface-400" /> Neutral</span>;
}
