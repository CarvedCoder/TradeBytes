/**
 * Leaderboard Page - Gamified competitive rankings with period selection,
 * podium display for top 3, and XP/streak badges.
 * Uses existing API endpoints unchanged.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { useAuthStore } from '@/stores/authStore';
import { formatPercent, cn } from '@/lib/utils';
import { Trophy, Medal, Crown, Star, Flame } from 'lucide-react';

type Period = 'daily' | 'weekly' | 'monthly' | 'all_time';

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<Period>('weekly');
  const user = useAuthStore((s) => s.user);

  const { data: leaderboard } = useQuery({
    queryKey: ['leaderboard', period],
    queryFn: () => api.get(`/leaderboard?period=${period}`).then((r) => r.data),
  });

  const { data: myRank } = useQuery({
    queryKey: ['my-rank'],
    queryFn: () => api.get('/leaderboard/me').then((r) => r.data),
  });

  const entries = leaderboard?.entries ?? [];
  const top3 = entries.slice(0, 3);
  const rest = entries.slice(3);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-warning/15">
            <Trophy className="h-5 w-5 text-warning" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Leaderboard</h1>
            <p className="text-sm text-surface-400">Compete with traders worldwide</p>
          </div>
        </div>

        {/* Period Selector */}
        <div className="flex rounded-xl border border-surface-700 bg-surface-800 p-1">
          {(['daily', 'weekly', 'monthly', 'all_time'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={cn(
                'rounded-lg px-3 py-1.5 text-xs font-medium transition-all',
                period === p
                  ? 'bg-primary-600 text-white shadow-sm'
                  : 'text-surface-300 hover:text-white',
              )}
            >
              {p.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* My Rank Card */}
      {myRank && (
        <div className="card-gamified border-primary-500/20 p-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="relative">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary-600 to-primary-500 text-lg font-bold text-white shadow-lg shadow-primary-500/25">
                  {user?.display_name?.charAt(0).toUpperCase() ?? '?'}
                </div>
                <div className="absolute -bottom-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-surface-900 text-[9px] font-bold text-primary-300 ring-2 ring-surface-900">
                  {myRank.level ?? user?.level ?? 1}
                </div>
              </div>
              <div>
                <p className="font-semibold text-white">{user?.display_name ?? 'You'}</p>
                <div className="flex items-center gap-3 text-xs text-surface-300">
                  <span className="flex items-center gap-1 text-xp">
                    <Star className="h-3 w-3" /> {(myRank.total_xp ?? 0).toLocaleString()} XP
                  </span>
                  {myRank.current_streak > 0 && (
                    <span className="flex items-center gap-1 text-streak">
                      <Flame className="h-3 w-3" /> {myRank.current_streak}d
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="text-right">
              <span className="text-3xl font-bold text-primary-300">#{myRank.rank}</span>
              <p className="text-[10px] text-surface-400">{period.replace('_', ' ')} ranking</p>
            </div>
          </div>
        </div>
      )}

      {/* Top 3 Podium */}
      {top3.length >= 3 && (
        <div className="grid grid-cols-3 gap-3">
          {/* 2nd place */}
          <PodiumCard entry={top3[1]} rank={2} userId={user?.id} />
          {/* 1st place */}
          <PodiumCard entry={top3[0]} rank={1} userId={user?.id} />
          {/* 3rd place */}
          <PodiumCard entry={top3[2]} rank={3} userId={user?.id} />
        </div>
      )}

      {/* Rankings Table */}
      <div className="card-gamified">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-700 text-left text-xs text-surface-400">
              <th className="pb-3 pl-4">Rank</th>
              <th className="pb-3">Trader</th>
              <th className="pb-3 text-right">XP</th>
              <th className="pb-3 text-right">Win Rate</th>
              <th className="pb-3 text-right">Return</th>
              <th className="pb-3 text-right pr-4">Streak</th>
            </tr>
          </thead>
          <tbody>
            {(top3.length >= 3 ? rest : entries).map((entry: any, i: number) => {
              const rank = top3.length >= 3 ? i + 4 : i + 1;
              const isMe = entry.user_id === user?.id;
              return (
                <tr
                  key={entry.user_id || i}
                  className={cn(
                    'border-b border-surface-800/50 transition-colors hover:bg-surface-800/30',
                    isMe && 'bg-primary-500/5',
                  )}
                >
                  <td className="py-3 pl-4">
                    <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-surface-800 text-xs font-medium text-surface-300">
                      {rank}
                    </span>
                  </td>
                  <td className="py-3">
                    <div className="flex items-center gap-2.5">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-600/60 text-xs font-bold text-white">
                        {entry.display_name?.charAt(0).toUpperCase() ?? '?'}
                      </div>
                      <span className={cn('text-sm font-medium', isMe ? 'text-primary-300' : 'text-white')}>
                        {entry.display_name}
                        {isMe && <span className="ml-1 text-[10px] text-primary-400">(You)</span>}
                      </span>
                    </div>
                  </td>
                  <td className="py-3 text-right">
                    <span className="font-mono text-sm text-xp">{entry.total_xp?.toLocaleString()}</span>
                  </td>
                  <td className="py-3 text-right text-sm text-white">
                    {formatPercent(entry.win_rate ?? 0)}
                  </td>
                  <td className={cn('py-3 text-right text-sm font-medium', (entry.total_return ?? 0) >= 0 ? 'text-success' : 'text-danger')}>
                    {formatPercent(entry.total_return ?? 0)}
                  </td>
                  <td className="py-3 text-right pr-4">
                    {(entry.current_streak ?? 0) > 0 ? (
                      <span className="inline-flex items-center gap-1 text-sm text-streak">
                        <Flame className="h-3 w-3" />
                        {entry.current_streak}
                      </span>
                    ) : (
                      <span className="text-sm text-surface-500">--</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>

        {!entries.length && (
          <div className="py-12 text-center text-surface-400">
            <Trophy className="mx-auto mb-3 h-10 w-10 text-surface-700" />
            <p className="text-sm font-medium">No leaderboard data yet</p>
            <p className="text-xs">Start trading to rank up!</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Podium Card for top 3
// ---------------------------------------------------------------------------
function PodiumCard({
  entry,
  rank,
  userId,
}: {
  entry: any;
  rank: number;
  userId?: string;
}) {
  const decor = getPodiumDecor(rank);
  const isMe = entry.user_id === userId;

  return (
    <div className={cn(
      'card-gamified flex flex-col items-center p-5 text-center',
      rank === 1 && 'border-yellow-400/20 lg:-mt-4',
    )}>
      {/* Rank Icon */}
      <div className="mb-3">{decor.icon}</div>

      {/* Avatar */}
      <div className={cn(
        'mb-2 flex h-14 w-14 items-center justify-center rounded-2xl text-lg font-bold text-white',
        decor.ring,
        'bg-gradient-to-br from-primary-600 to-primary-500',
      )}>
        {entry.display_name?.charAt(0).toUpperCase() ?? '?'}
      </div>

      <p className={cn('text-sm font-semibold', isMe ? 'text-primary-300' : 'text-white')}>
        {entry.display_name}
      </p>
      <p className="mt-1 font-mono text-xs text-xp">{(entry.total_xp ?? 0).toLocaleString()} XP</p>
      {(entry.current_streak ?? 0) > 0 && (
        <div className="mt-1 flex items-center gap-0.5 text-[10px] text-streak">
          <Flame className="h-2.5 w-2.5" /> {entry.current_streak}d streak
        </div>
      )}
    </div>
  );
}

function getPodiumDecor(rank: number) {
  if (rank === 1) return { icon: <Crown className="h-7 w-7 text-yellow-400 drop-shadow-lg" />, ring: 'ring-2 ring-yellow-400/50 shadow-lg shadow-yellow-400/20' };
  if (rank === 2) return { icon: <Medal className="h-6 w-6 text-gray-300" />, ring: 'ring-2 ring-gray-300/30' };
  return { icon: <Medal className="h-6 w-6 text-amber-600" />, ring: 'ring-2 ring-amber-600/30' };
}
