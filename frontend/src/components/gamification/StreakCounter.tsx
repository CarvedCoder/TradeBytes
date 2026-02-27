/**
 * StreakCounter - Animated flame streak display with pulse effect on long streaks.
 * Pulls streak value from existing backend endpoint only.
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { Flame } from 'lucide-react';

interface StreakCounterProps {
  streak: number;
  longestStreak?: number;
  variant?: 'compact' | 'full';
  className?: string;
}

function StreakCounterComponent({
  streak,
  longestStreak,
  variant = 'full',
  className,
}: StreakCounterProps) {
  const isHotStreak = streak >= 7;
  const isOnFire = streak >= 30;

  if (variant === 'compact') {
    return (
      <div
        className={cn(
          'flex items-center gap-1 rounded-full px-2.5 py-1',
          isOnFire
            ? 'bg-danger/15 text-danger'
            : isHotStreak
              ? 'bg-streak/15 text-streak'
              : 'bg-surface-800 text-surface-300',
          isHotStreak && 'animate-streak-pulse',
          className,
        )}
      >
        <Flame className={cn('h-3.5 w-3.5', isOnFire ? 'text-danger' : isHotStreak ? 'text-streak' : 'text-surface-400')} />
        <span className="font-mono text-xs font-bold">{streak}</span>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-xl border p-3 transition-all',
        isOnFire
          ? 'border-danger/30 bg-danger/5'
          : isHotStreak
            ? 'border-streak/30 bg-streak/5'
            : 'border-surface-700 bg-surface-800/50',
        className,
      )}
    >
      <div
        className={cn(
          'flex h-10 w-10 items-center justify-center rounded-lg',
          isOnFire
            ? 'bg-danger/20'
            : isHotStreak
              ? 'bg-streak/20'
              : 'bg-surface-800',
        )}
      >
        <Flame
          className={cn(
            'h-5 w-5',
            isOnFire ? 'text-danger' : isHotStreak ? 'text-streak' : 'text-surface-400',
            isHotStreak && 'animate-flame-flicker',
          )}
        />
      </div>

      <div className="flex-1">
        <div className="flex items-baseline gap-1">
          <span
            className={cn(
              'text-xl font-bold tabular-nums',
              isOnFire ? 'text-danger' : isHotStreak ? 'text-streak' : 'text-white',
            )}
          >
            {streak}
          </span>
          <span className="text-xs text-surface-300">day streak</span>
        </div>
        {longestStreak !== undefined && longestStreak > 0 && (
          <p className="text-xs text-surface-400">
            Best: {longestStreak} days
          </p>
        )}
      </div>

      {isHotStreak && (
        <span className="badge-streak text-[10px]">
          {isOnFire ? 'ON FIRE' : 'HOT'}
        </span>
      )}
    </div>
  );
}

export const StreakCounter = memo(StreakCounterComponent);
export default StreakCounter;
