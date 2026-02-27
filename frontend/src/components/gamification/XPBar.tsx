/**
 * XPBar - Animated XP progress bar with level display and gain indicator.
 * Uses backend-provided XP data only.
 */

import { useState, useEffect, memo } from 'react';
import { cn } from '@/lib/utils';
import { Star, ChevronUp } from 'lucide-react';

interface XPBarProps {
  currentXp: number;
  xpToNextLevel: number;
  level: number;
  recentXpGain?: number | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

function XPBarComponent({
  currentXp,
  xpToNextLevel,
  level,
  recentXpGain,
  size = 'md',
  showLabel = true,
  className,
}: XPBarProps) {
  const [showGain, setShowGain] = useState(false);
  const percent = Math.min((currentXp / Math.max(xpToNextLevel, 1)) * 100, 100);

  useEffect(() => {
    if (recentXpGain && recentXpGain > 0) {
      setShowGain(true);
      const timer = setTimeout(() => setShowGain(false), 1200);
      return () => clearTimeout(timer);
    }
  }, [recentXpGain]);

  const barHeight = size === 'sm' ? 'h-1.5' : size === 'lg' ? 'h-4' : 'h-2.5';

  return (
    <div className={cn('relative', className)}>
      {showLabel && (
        <div className="mb-1.5 flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <Star className="h-3.5 w-3.5 text-xp" />
            <span className="text-xs font-semibold text-xp">Level {level}</span>
          </div>
          <span className="font-mono text-xs text-surface-300">
            {currentXp.toLocaleString()} / {xpToNextLevel.toLocaleString()} XP
          </span>
        </div>
      )}

      <div className={cn('overflow-hidden rounded-full bg-surface-800', barHeight)}>
        <div
          className={cn(
            'h-full rounded-full bg-gradient-to-r from-amber-500 via-xp to-yellow-300 transition-all duration-700 ease-out',
            size === 'lg' && 'shadow-[0_0_12px_rgba(251,191,36,0.4)]',
          )}
          style={{ width: `${percent}%` }}
        />
      </div>

      {showGain && recentXpGain && (
        <div className="absolute -top-5 right-0 flex items-center gap-0.5 animate-xp-float">
          <ChevronUp className="h-3 w-3 text-xp" />
          <span className="font-mono text-xs font-bold text-xp">
            +{recentXpGain} XP
          </span>
        </div>
      )}
    </div>
  );
}

export const XPBar = memo(XPBarComponent);
export default XPBar;
