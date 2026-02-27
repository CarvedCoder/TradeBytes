/**
 * Leaderboard Page - Competitive rankings with period selection.
 */

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '@/lib/api';
import { formatPercent, cn } from '@/lib/utils';
import { Trophy, Medal, Crown, Star } from 'lucide-react';

type Period = 'daily' | 'weekly' | 'monthly' | 'all_time';

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<Period>('weekly');

  const { data: leaderboard } = useQuery({
    queryKey: ['leaderboard', period],
    queryFn: () => api.get(`/leaderboard?period=${period}`).then((r) => r.data),
  });

  const { data: myRank } = useQuery({
    queryKey: ['my-rank'],
    queryFn: () => api.get('/leaderboard/me').then((r) => r.data),
  });

  const getRankIcon = (rank: number) => {
    if (rank === 1) return <Crown className="h-5 w-5 text-yellow-400" />;
    if (rank === 2) return <Medal className="h-5 w-5 text-gray-300" />;
    if (rank === 3) return <Medal className="h-5 w-5 text-amber-600" />;
    return <span className="flex h-5 w-5 items-center justify-center text-xs text-surface-200">#{rank}</span>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Trophy className="h-6 w-6 text-warning" />
          <h1 className="text-2xl font-bold text-white">Leaderboard</h1>
        </div>

        {/* Period Selector */}
        <div className="flex rounded-lg bg-surface-800 p-1">
          {(['daily', 'weekly', 'monthly', 'all_time'] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={cn(
                'rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                period === p ? 'bg-primary-600 text-white' : 'text-surface-200 hover:text-white',
              )}
            >
              {p.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* My Rank */}
      {myRank && (
        <div className="card border-primary-500/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Star className="h-5 w-5 text-primary-400" />
              <span className="font-medium text-white">Your Rank</span>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold text-primary-300">#{myRank.rank}</span>
              <p className="text-xs text-surface-200">{myRank.total_xp} XP</p>
            </div>
          </div>
        </div>
      )}

      {/* Rankings Table */}
      <div className="card">
        <table className="w-full">
          <thead>
            <tr className="border-b border-surface-700 text-left text-xs text-surface-200">
              <th className="pb-3 pl-2">Rank</th>
              <th className="pb-3">Trader</th>
              <th className="pb-3 text-right">XP</th>
              <th className="pb-3 text-right">Win Rate</th>
              <th className="pb-3 text-right">Return</th>
              <th className="pb-3 text-right">Streak</th>
            </tr>
          </thead>
          <tbody>
            {(leaderboard?.entries ?? []).map((entry: any, i: number) => (
              <tr
                key={entry.user_id || i}
                className={cn(
                  'border-b border-surface-800 transition-colors hover:bg-surface-800',
                  i < 3 && 'bg-surface-800/50',
                )}
              >
                <td className="py-3 pl-2">{getRankIcon(i + 1)}</td>
                <td className="py-3">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-600 text-xs font-bold">
                      {entry.display_name?.charAt(0).toUpperCase() ?? '?'}
                    </div>
                    <span className="text-sm font-medium text-white">{entry.display_name}</span>
                  </div>
                </td>
                <td className="py-3 text-right font-mono text-sm text-white">
                  {entry.total_xp?.toLocaleString()}
                </td>
                <td className="py-3 text-right text-sm text-white">
                  {formatPercent(entry.win_rate ?? 0)}
                </td>
                <td className={cn('py-3 text-right text-sm font-medium', (entry.total_return ?? 0) >= 0 ? 'text-success' : 'text-danger')}>
                  {formatPercent(entry.total_return ?? 0)}
                </td>
                <td className="py-3 text-right text-sm text-warning">
                  {entry.current_streak ?? 0}🔥
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {!leaderboard?.entries?.length && (
          <div className="py-8 text-center text-surface-200">
            <Trophy className="mx-auto mb-2 h-8 w-8 text-surface-700" />
            <p>No leaderboard data yet. Start trading to rank up!</p>
          </div>
        )}
      </div>
    </div>
  );
}
