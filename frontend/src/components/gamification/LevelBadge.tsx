/**
 * LevelBadge - Displays user level with a styled badge and optional label.
 * Animate on level-up with spring effect.
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';
import { Shield } from 'lucide-react';

interface LevelBadgeProps {
  level: number;
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

function getLevelTier(level: number) {
  if (level >= 50) return { label: 'Legendary', color: 'text-legendary', bg: 'bg-legendary/15', border: 'border-legendary/30', glow: 'shadow-legendary/20' };
  if (level >= 30) return { label: 'Master', color: 'text-xp', bg: 'bg-xp/15', border: 'border-xp/30', glow: 'shadow-xp/20' };
  if (level >= 15) return { label: 'Expert', color: 'text-primary-400', bg: 'bg-primary-400/15', border: 'border-primary-400/30', glow: 'shadow-primary-400/20' };
  if (level >= 5) return { label: 'Apprentice', color: 'text-accent-400', bg: 'bg-accent-400/15', border: 'border-accent-400/30', glow: 'shadow-accent-400/20' };
  return { label: 'Novice', color: 'text-surface-300', bg: 'bg-surface-800', border: 'border-surface-700', glow: '' };
}

function LevelBadgeComponent({ level, size = 'md', animated = false, className }: LevelBadgeProps) {
  const tier = getLevelTier(level);

  const sizeClasses = {
    sm: 'h-7 w-7 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-14 w-14 text-lg',
  };

  const iconSize = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-6 w-6',
  };

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div
        className={cn(
          'relative flex items-center justify-center rounded-xl border font-bold',
          sizeClasses[size],
          tier.bg,
          tier.border,
          tier.color,
          tier.glow && `shadow-lg ${tier.glow}`,
          animated && 'animate-level-up',
        )}
      >
        <Shield className={cn('absolute opacity-10', iconSize[size])} />
        <span className="relative z-10">{level}</span>
      </div>
      {size !== 'sm' && (
        <div>
          <p className={cn('text-xs font-semibold', tier.color)}>{tier.label}</p>
          <p className="text-[10px] text-surface-400">Level {level}</p>
        </div>
      )}
    </div>
  );
}

export const LevelBadge = memo(LevelBadgeComponent);
export default LevelBadge;
