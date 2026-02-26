/**
 * Learning Paths Page - Gamified learning modules with progress tracking.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '@/lib/api';
import { cn } from '@/lib/utils';
import { GraduationCap, CheckCircle2, Circle, Lock, ArrowRight, BookOpen, Star } from 'lucide-react';

export default function LearningPage() {
  const queryClient = useQueryClient();

  const { data: paths } = useQuery({
    queryKey: ['learning-paths'],
    queryFn: () => api.get('/learning/paths').then((r) => r.data),
  });

  const enroll = useMutation({
    mutationFn: (slug: string) => api.post(`/learning/${slug}/enroll`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['learning-paths'] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <GraduationCap className="h-6 w-6 text-accent-400" />
        <h1 className="text-2xl font-bold text-white">Learning Paths</h1>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {(paths?.paths ?? []).map((path: any) => (
          <div key={path.slug} className="card-hover flex flex-col">
            <div className="mb-3 flex items-center justify-between">
              <span className={cn(
                'badge',
                path.difficulty === 'beginner' ? 'badge-success' :
                path.difficulty === 'intermediate' ? 'badge-warning' : 'badge-danger'
              )}>
                {path.difficulty}
              </span>
              <div className="flex items-center gap-1 text-xs text-warning">
                <Star className="h-3 w-3" />
                <span>{path.xp_reward} XP</span>
              </div>
            </div>

            <h3 className="mb-2 text-lg font-semibold text-white">{path.title}</h3>
            <p className="mb-4 flex-1 text-sm text-surface-200">{path.description}</p>

            {/* Progress */}
            {path.enrolled && (
              <div className="mb-4">
                <div className="mb-1 flex justify-between text-xs text-surface-200">
                  <span>{path.completed_modules}/{path.total_modules} modules</span>
                  <span>{Math.round((path.completed_modules / path.total_modules) * 100)}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-700">
                  <div
                    className="h-full rounded-full bg-accent-500 transition-all"
                    style={{ width: `${(path.completed_modules / path.total_modules) * 100}%` }}
                  />
                </div>
              </div>
            )}

            {/* Modules Preview */}
            <div className="mb-4 space-y-1.5">
              {(path.modules ?? []).slice(0, 4).map((mod: any, i: number) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  {mod.completed ? (
                    <CheckCircle2 className="h-4 w-4 text-accent-400" />
                  ) : mod.locked ? (
                    <Lock className="h-4 w-4 text-surface-700" />
                  ) : (
                    <Circle className="h-4 w-4 text-surface-200" />
                  )}
                  <span className={cn(
                    mod.completed ? 'text-surface-200 line-through' : 
                    mod.locked ? 'text-surface-700' : 'text-white'
                  )}>
                    {mod.title}
                  </span>
                </div>
              ))}
              {(path.modules?.length ?? 0) > 4 && (
                <p className="text-xs text-surface-200">+{path.modules.length - 4} more modules</p>
              )}
            </div>

            {/* Action */}
            {path.enrolled ? (
              <button className="btn-primary mt-auto flex items-center justify-center gap-2">
                <BookOpen className="h-4 w-4" /> Continue Learning
              </button>
            ) : (
              <button
                onClick={() => enroll.mutate(path.slug)}
                className="btn-secondary mt-auto flex items-center justify-center gap-2"
              >
                Enroll <ArrowRight className="h-4 w-4" />
              </button>
            )}
          </div>
        ))}

        {!paths?.paths?.length && (
          <div className="col-span-full py-12 text-center text-surface-200">
            <GraduationCap className="mx-auto mb-3 h-12 w-12 text-surface-700" />
            <p className="text-lg">Learning paths coming soon!</p>
            <p className="text-sm">We're building courses on technical analysis, options, and more.</p>
          </div>
        )}
      </div>
    </div>
  );
}
