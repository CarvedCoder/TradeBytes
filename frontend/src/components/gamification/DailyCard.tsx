/**
 * DailyCard - Daily Challenge card with difficulty badge, XP reward, completion status, and CTA.
 * Calls existing daily challenge endpoint. Respects backend completion state.
 */

import { memo } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Zap, ArrowRight, CheckCircle2, Clock, Star } from 'lucide-react';
import ProgressRing from './ProgressRing';

interface DailyChallengeData {
  title?: string;
  description?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
  xp_reward?: number;
  completed?: boolean;
  time_remaining?: string;
}

interface DailyCardProps {
  challenge?: DailyChallengeData | null;
  isLoading?: boolean;
  className?: string;
}

function getDifficultyConfig(difficulty?: string) {
  switch (difficulty) {
    case 'easy': return { label: 'Easy', color: 'badge-success' };
    case 'hard': return { label: 'Hard', color: 'badge-danger' };
    default: return { label: 'Medium', color: 'badge-warning' };
  }
}

function DailyCardComponent({ challenge, isLoading, className }: DailyCardProps) {
  const diff = getDifficultyConfig(challenge?.difficulty);
  const isComplete = challenge?.completed ?? false;

  if (isLoading) {
    return (
      <div className={cn('card-gamified p-5', className)}>
        <div className="flex animate-pulse items-center gap-3">
          <div className="h-12 w-12 rounded-xl bg-surface-800" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-2/3 rounded bg-surface-800" />
            <div className="h-3 w-1/3 rounded bg-surface-800" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'card-gamified p-5',
        isComplete && 'border-success/20',
        className,
      )}
    >
      {/* Header */}
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-xl',
              isComplete ? 'bg-success/15' : 'bg-warning/15',
            )}
          >
            {isComplete ? (
              <CheckCircle2 className="h-5 w-5 text-success" />
            ) : (
              <Zap className="h-5 w-5 text-warning" />
            )}
          </div>
          <div>
            <p className="text-[10px] font-medium uppercase tracking-wider text-surface-400">
              Daily Challenge
            </p>
            <h3 className="text-sm font-semibold text-white">
              {challenge?.title ?? 'Today\'s Challenge'}
            </h3>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={diff.color}>{diff.label}</span>
          <span className="badge-xp flex items-center gap-1">
            <Star className="h-3 w-3" />
            {challenge?.xp_reward ?? 50} XP
          </span>
        </div>
      </div>

      {/* Description */}
      <p className="mb-4 text-sm text-surface-300">
        {challenge?.description ?? 'Complete this challenge to earn XP and maintain your streak.'}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between">
        {isComplete ? (
          <div className="flex items-center gap-2 text-sm text-success">
            <CheckCircle2 className="h-4 w-4" />
            <span className="font-medium">Completed</span>
          </div>
        ) : (
          <Link to="/simulation" className="btn-gamified inline-flex items-center gap-2 text-sm">
            Start Challenge <ArrowRight className="h-4 w-4" />
          </Link>
        )}

        {challenge?.time_remaining && !isComplete && (
          <div className="flex items-center gap-1 text-xs text-surface-400">
            <Clock className="h-3 w-3" />
            <span>{challenge.time_remaining} left</span>
          </div>
        )}
      </div>
    </div>
  );
}

export const DailyCard = memo(DailyCardComponent);
export default DailyCard;
