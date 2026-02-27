/**
 * LeaderboardPreview - Compact top-5 leaderboard for the dashboard.
 * Uses existing leaderboard endpoint. Highlights current user.
 */

import { memo } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Trophy, Crown, Medal, ArrowRight, Flame } from 'lucide-react';

interface LeaderboardEntry {
  user_id?: string;
  display_name: string;
  total_xp: number;
  current_streak?: number;
  is_current_user?: boolean;
}

interface LeaderboardPreviewProps {
  entries?: LeaderboardEntry[];
  myRank?: number;
  isLoading?: boolean;
  className?: string;
}

function getRankIcon(rank: number) {
  if (rank === 1) return <Crown className="h-4 w-4 text-yellow-400" />;
  if (rank === 2) return <Medal className="h-4 w-4 text-gray-300" />;
  if (rank === 3) return <Medal className="h-4 w-4 text-amber-600" />;
  return <span className="flex h-4 w-4 items-center justify-center text-[10px] text-surface-400">#{rank}</span>;
}

function getRankBg(rank: number) {
  if (rank === 1) return 'bg-yellow-400/5';
  if (rank === 2) return 'bg-gray-300/5';
  if (rank === 3) return 'bg-amber-600/5';
  return '';
}

function LeaderboardPreviewComponent({
  entries = [],
  myRank,
  isLoading,
  className,
}: LeaderboardPreviewProps) {
  return (
    <div className={cn('card-gamified', className)}>
      {/* Header */}
      <div className="mb-4 flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Trophy className="h-4 w-4 text-warning" />
          <h3 className="text-sm font-semibold text-white">Leaderboard</h3>
        </div>
        <Link to="/leaderboard" className="flex items-center gap-1 text-xs text-primary-400 hover:text-primary-300">
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </div>

      {/* Entries */}
      <div className="space-y-1">
        {isLoading && (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex animate-pulse items-center gap-3 rounded-lg px-3 py-2">
              <div className="h-4 w-4 rounded bg-surface-800" />
              <div className="h-6 w-6 rounded-full bg-surface-800" />
              <div className="flex-1">
                <div className="h-3 w-20 rounded bg-surface-800" />
              </div>
              <div className="h-3 w-12 rounded bg-surface-800" />
            </div>
          ))
        )}

        {entries.slice(0, 5).map((entry, i) => (
          <div
            key={entry.user_id || i}
            className={cn(
              'flex items-center gap-3 rounded-lg px-3 py-2 transition-colors',
              getRankBg(i + 1),
              entry.is_current_user && 'border border-primary-500/30 bg-primary-500/5',
            )}
          >
            <div className="w-5 text-center">{getRankIcon(i + 1)}</div>
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-600/80 text-[10px] font-bold text-white">
              {entry.display_name?.charAt(0).toUpperCase() ?? '?'}
            </div>
            <div className="flex-1 min-w-0">
              <p className={cn(
                'truncate text-xs font-medium',
                entry.is_current_user ? 'text-primary-300' : 'text-white',
              )}>
                {entry.display_name}
                {entry.is_current_user && (
                  <span className="ml-1 text-[10px] text-primary-400">(You)</span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2 text-right">
              <span className="font-mono text-xs text-xp">{entry.total_xp?.toLocaleString()}</span>
              {entry.current_streak && entry.current_streak > 0 && (
                <div className="flex items-center gap-0.5">
                  <Flame className="h-3 w-3 text-streak" />
                  <span className="font-mono text-[10px] text-streak">{entry.current_streak}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Your Rank */}
      {myRank && myRank > 5 && (
        <div className="mt-3 border-t border-surface-700/50 pt-3">
          <div className="flex items-center justify-between rounded-lg bg-primary-500/5 px-3 py-2">
            <span className="text-xs text-surface-300">Your Rank</span>
            <span className="font-mono text-sm font-bold text-primary-300">#{myRank}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export const LeaderboardPreview = memo(LeaderboardPreviewComponent);
export default LeaderboardPreview;
