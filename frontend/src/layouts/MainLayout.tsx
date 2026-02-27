/**
 * Main Layout - Sidebar navigation + content area with gamification visuals.
 * Preserves existing routing and auth flow.
 */

import { Outlet, NavLink, useLocation } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import { useGamificationStore } from '@/stores/gamificationStore';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  LineChart,
  Briefcase,
  Newspaper,
  Trophy,
  GraduationCap,
  Users,
  Bot,
  LogOut,
  Flame,
  Star,
  Shield,
  ChevronUp,
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/simulation', icon: LineChart, label: 'Simulation' },
  { to: '/portfolio', icon: Briefcase, label: 'Portfolio' },
  { to: '/news', icon: Newspaper, label: 'News Intel' },
  { to: '/leaderboard', icon: Trophy, label: 'Leaderboard' },
  { to: '/learning', icon: GraduationCap, label: 'Learning' },
  { to: '/community', icon: Users, label: 'Community' },
  { to: '/advisor', icon: Bot, label: 'AI Advisor' },
];

export default function MainLayout() {
  const { user, logout } = useAuthStore();
  const { level, currentStreak, totalXp, xpToNextLevel, recentXpGain } = useGamificationStore();
  const location = useLocation();

  const xpPercent = Math.min((totalXp / Math.max(xpToNextLevel, 1)) * 100, 100);
  const isHotStreak = currentStreak >= 7;

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-surface-700 bg-surface-900">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2.5 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary-600 to-primary-500 shadow-lg shadow-primary-600/20">
            <span className="text-sm font-bold text-white">TB</span>
          </div>
          <span className="text-lg font-bold text-white">TradeBytes</span>
        </div>

        {/* XP / Level / Streak Panel */}
        <div className="mx-4 mb-4 space-y-3 rounded-xl border border-surface-700 bg-surface-800/50 p-3">
          {/* Level + Streak Row */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-primary-500/30 bg-primary-500/10 text-xs font-bold text-primary-300">
                <Shield className="absolute h-3 w-3 opacity-20" />
                {level}
              </div>
              <div>
                <p className="text-xs font-semibold text-white">Level {level}</p>
                <p className="text-[10px] text-surface-400">
                  {totalXp.toLocaleString()} / {xpToNextLevel.toLocaleString()} XP
                </p>
              </div>
            </div>
            <div
              className={cn(
                'flex items-center gap-1 rounded-full px-2 py-0.5',
                isHotStreak
                  ? 'bg-streak/15 text-streak'
                  : 'bg-surface-700 text-surface-300',
              )}
            >
              <Flame
                className={cn(
                  'h-3 w-3',
                  isHotStreak ? 'text-streak animate-flame-flicker' : 'text-surface-400',
                )}
              />
              <span className="font-mono text-[11px] font-bold">{currentStreak}</span>
            </div>
          </div>

          {/* XP Progress Bar */}
          <div>
            <div className="h-2 overflow-hidden rounded-full bg-surface-700">
              <div
                className="h-full rounded-full bg-gradient-to-r from-amber-500 via-xp to-yellow-300 transition-all duration-700 ease-out"
                style={{ width: `${xpPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 overflow-auto px-3">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'bg-primary-600/15 text-primary-300 shadow-sm'
                    : 'text-surface-300 hover:bg-surface-800 hover:text-white',
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
              {to === '/leaderboard' && (
                <span className="ml-auto flex h-4 w-4 items-center justify-center rounded-full bg-warning/20 text-[9px] font-bold text-warning">
                  <Trophy className="h-2.5 w-2.5" />
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-surface-700 p-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-primary-600 to-primary-500 text-sm font-bold text-white">
                {user?.display_name?.charAt(0).toUpperCase() ?? '?'}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-surface-900 text-[8px] font-bold text-primary-300">
                {level}
              </div>
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium text-white">
                {user?.display_name ?? 'Trader'}
              </p>
              <div className="flex items-center gap-2 text-[10px]">
                <span className="flex items-center gap-0.5 text-xp">
                  <Star className="h-2.5 w-2.5" />
                  {totalXp.toLocaleString()} XP
                </span>
                <span className="flex items-center gap-0.5 text-streak">
                  <Flame className="h-2.5 w-2.5" />
                  {currentStreak}d
                </span>
              </div>
            </div>
            <button onClick={logout} className="rounded-lg p-1.5 text-surface-400 transition-colors hover:bg-surface-800 hover:text-danger" title="Logout">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto bg-surface-950">
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
