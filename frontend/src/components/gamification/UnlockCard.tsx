/**
 * UnlockCard - Learning path item with locked/unlocked states.
 * Uses backend unlock status. Locked state shows grayed-out card with lock icon.
 * Unlocked state is clickable and navigates to existing route.
 */

import { memo } from 'react';
import { Link } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Lock, CheckCircle2, ArrowRight, Star, BookOpen } from 'lucide-react';
import ProgressRing from './ProgressRing';

interface UnlockCardProps {
  title: string;
  description?: string;
  xpReward?: number;
  difficulty?: string;
  locked?: boolean;
  completed?: boolean;
  progress?: number; // 0-100
  lockReason?: string;
  href?: string;
  className?: string;
}

function UnlockCardComponent({
  title,
  description,
  xpReward,
  difficulty,
  locked = false,
  completed = false,
  progress = 0,
  lockReason,
  href = '/learning',
  className,
}: UnlockCardProps) {
  const content = (
    <div
      className={cn(
        'card-gamified relative flex items-center gap-4 p-4',
        locked && 'pointer-events-none opacity-50 grayscale',
        completed && 'border-success/20',
        className,
      )}
    >
      {/* Progress Ring / Status */}
      <ProgressRing
        progress={completed ? 100 : progress}
        size={48}
        strokeWidth={3}
        color={completed ? 'stroke-success' : locked ? 'stroke-surface-600' : 'stroke-primary-500'}
      >
        {completed ? (
          <CheckCircle2 className="h-5 w-5 text-success" />
        ) : locked ? (
          <Lock className="h-4 w-4 text-surface-500" />
        ) : (
          <BookOpen className="h-4 w-4 text-primary-400" />
        )}
      </ProgressRing>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h4 className={cn(
            'truncate text-sm font-semibold',
            locked ? 'text-surface-500' : 'text-white',
          )}>
            {title}
          </h4>
          {difficulty && (
            <span className={cn(
              'badge text-[10px]',
              difficulty === 'beginner' ? 'badge-success' :
              difficulty === 'intermediate' ? 'badge-warning' : 'badge-danger',
            )}>
              {difficulty}
            </span>
          )}
        </div>
        <p className={cn(
          'mt-0.5 truncate text-xs',
          locked ? 'text-surface-600' : 'text-surface-300',
        )}>
          {locked && lockReason ? lockReason : description}
        </p>
      </div>

      {/* Right side */}
      <div className="flex flex-shrink-0 items-center gap-2">
        {xpReward && (
          <span className={cn('badge-xp text-[10px]', locked && 'opacity-40')}>
            <Star className="mr-0.5 h-2.5 w-2.5" />
            {xpReward} XP
          </span>
        )}
        {!locked && !completed && (
          <ArrowRight className="h-4 w-4 text-surface-400" />
        )}
      </div>
    </div>
  );

  if (locked || completed) return content;

  return (
    <Link to={href} className="block">
      {content}
    </Link>
  );
}

export const UnlockCard = memo(UnlockCardComponent);
export default UnlockCard;
