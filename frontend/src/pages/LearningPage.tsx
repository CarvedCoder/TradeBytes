/**
 * Learning Paths Page - Gamified learning modules with progress tracking,
 * lock/unlock states, XP rewards, and progress rings.
 * Uses existing API endpoints unchanged.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { useGamificationStore } from '@/stores/gamificationStore';
import { cn } from '@/lib/utils';
import {
  GraduationCap,
  CheckCircle2,
  Circle,
  Lock,
  ArrowRight,
  BookOpen,
  Star,
  Zap,
  Trophy,
} from 'lucide-react';
import { ProgressRing, XPBar, LevelBadge } from '@/components/gamification';

export default function LearningPage() {
  const queryClient = useQueryClient();
  const { level, totalXp, xpToNextLevel } = useGamificationStore();

  const { data: paths } = useQuery({
    queryKey: ['learning-paths'],
    queryFn: () => api.get('/learning/paths').then((r) => r.data),
  });

  const enroll = useMutation({
    mutationFn: (slug: string) => api.post(`/learning/${slug}/enroll`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['learning-paths'] }),
  });

  const allPaths = paths?.paths ?? [];
  const enrolledPaths = allPaths.filter((p: any) => p.enrolled);
  const availablePaths = allPaths.filter((p: any) => !p.enrolled);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-500/15">
            <GraduationCap className="h-5 w-5 text-accent-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Learning Paths</h1>
            <p className="text-sm text-surface-400">Master finance through structured courses</p>
          </div>
        </div>
        <LevelBadge level={level} size="md" />
      </div>

      {/* XP Progress */}
      <div className="card-gamified p-4">
        <div className="flex items-center gap-6">
          <ProgressRing
            progress={(totalXp / Math.max(xpToNextLevel, 1)) * 100}
            size={56}
            strokeWidth={4}
            color="stroke-xp"
          >
            <span className="text-xs font-bold text-xp">{level}</span>
          </ProgressRing>
          <div className="flex-1">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-xs font-medium text-surface-300">Learning Progress</span>
              <span className="font-mono text-xs text-xp">{totalXp.toLocaleString()} XP</span>
            </div>
            <XPBar
              currentXp={totalXp}
              xpToNextLevel={xpToNextLevel}
              level={level}
              size="sm"
              showLabel={false}
            />
            <p className="mt-1 text-[10px] text-surface-400">
              {(xpToNextLevel - totalXp).toLocaleString()} XP to Level {level + 1}
            </p>
          </div>
        </div>
      </div>

      {/* Enrolled / In-Progress Paths */}
      {enrolledPaths.length > 0 && (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-primary-400" />
            <h2 className="text-sm font-semibold text-white">Continue Learning</h2>
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {enrolledPaths.map((path: any) => (
              <PathCard key={path.slug} path={path} variant="enrolled" />
            ))}
          </div>
        </section>
      )}

      {/* Available Paths */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Zap className="h-4 w-4 text-warning" />
          <h2 className="text-sm font-semibold text-white">
            {enrolledPaths.length > 0 ? 'Explore More' : 'All Courses'}
          </h2>
        </div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {availablePaths.map((path: any) => (
            <PathCard
              key={path.slug}
              path={path}
              variant="available"
              onEnroll={() => enroll.mutate(path.slug)}
              isEnrolling={enroll.isPending}
            />
          ))}
        </div>
      </section>

      {/* Empty State */}
      {!allPaths.length && (
        <div className="card-gamified py-16 text-center">
          <GraduationCap className="mx-auto mb-4 h-12 w-12 text-surface-700" />
          <p className="text-lg font-medium text-white">Learning paths coming soon!</p>
          <p className="mt-1 text-sm text-surface-400">We are building courses on technical analysis, options, and more.</p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Path Card
// ---------------------------------------------------------------------------
function PathCard({
  path,
  variant,
  onEnroll,
  isEnrolling,
}: {
  path: any;
  variant: 'enrolled' | 'available';
  onEnroll?: () => void;
  isEnrolling?: boolean;
}) {
  const progress = path.total_modules > 0
    ? Math.round((path.completed_modules / path.total_modules) * 100)
    : 0;
  const isComplete = path.completed_modules === path.total_modules && path.total_modules > 0;

  return (
    <div className={cn(
      'card-gamified flex flex-col p-5',
      isComplete && 'border-success/20',
      variant === 'enrolled' && 'border-primary-500/15',
    )}>
      {/* Top Row */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={cn(
            'badge text-[10px]',
            path.difficulty === 'beginner' ? 'badge-success' :
            path.difficulty === 'intermediate' ? 'badge-warning' : 'badge-danger',
          )}>
            {path.difficulty}
          </span>
          {isComplete && <span className="badge-success text-[10px]">Completed</span>}
        </div>
        <span className="badge-xp flex items-center gap-1 text-[10px]">
          <Star className="h-2.5 w-2.5" />
          {path.xp_reward} XP
        </span>
      </div>

      {/* Title + Description */}
      <h3 className="mb-1 text-base font-semibold text-white">{path.title}</h3>
      <p className="mb-4 flex-1 text-xs text-surface-300 line-clamp-2">{path.description}</p>

      {/* Progress (enrolled only) */}
      {variant === 'enrolled' && (
        <div className="mb-4">
          <div className="mb-1.5 flex justify-between text-[10px]">
            <span className="text-surface-400">{path.completed_modules}/{path.total_modules} modules</span>
            <span className={cn('font-bold', isComplete ? 'text-success' : 'text-primary-300')}>{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-800">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                isComplete
                  ? 'bg-gradient-to-r from-success/80 to-success'
                  : 'bg-gradient-to-r from-primary-500/80 to-primary-400',
              )}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Modules Preview */}
      <div className="mb-4 space-y-1.5">
        {(path.modules ?? []).slice(0, 4).map((mod: any, i: number) => (
          <div key={i} className="flex items-center gap-2 text-xs">
            {mod.completed ? (
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-success" />
            ) : mod.locked ? (
              <Lock className="h-3.5 w-3.5 shrink-0 text-surface-600" />
            ) : (
              <Circle className="h-3.5 w-3.5 shrink-0 text-surface-400" />
            )}
            <span className={cn(
              mod.completed ? 'text-surface-400 line-through' :
              mod.locked ? 'text-surface-600' : 'text-surface-200',
            )}>
              {mod.title}
            </span>
          </div>
        ))}
        {(path.modules?.length ?? 0) > 4 && (
          <p className="text-[10px] text-surface-500">+{path.modules.length - 4} more modules</p>
        )}
      </div>

      {/* Action */}
      {variant === 'enrolled' ? (
        <button className={cn(
          'mt-auto flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-all active:scale-95',
          isComplete
            ? 'bg-success/15 text-success hover:bg-success/20'
            : 'btn-gamified',
        )}>
          {isComplete ? (
            <><Trophy className="h-4 w-4" /> Review Course</>
          ) : (
            <><BookOpen className="h-4 w-4" /> Continue Learning</>
          )}
        </button>
      ) : (
        <button
          onClick={onEnroll}
          disabled={isEnrolling}
          className="btn-secondary mt-auto flex items-center justify-center gap-2 text-sm"
        >
          Enroll <ArrowRight className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
