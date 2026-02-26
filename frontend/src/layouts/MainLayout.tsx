/**
 * Main Layout - Sidebar navigation + content area.
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
  const { level, currentStreak, totalXp, xpToNextLevel } = useGamificationStore();
  const location = useLocation();

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-surface-700 bg-surface-900">
        {/* Logo */}
        <div className="flex h-16 items-center gap-2 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600">
            <span className="text-sm font-bold">TB</span>
          </div>
          <span className="text-lg font-bold text-white">TradeBytes</span>
        </div>

        {/* XP / Level Bar */}
        <div className="mx-4 mb-4 rounded-lg bg-surface-800 p-3">
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="font-medium text-primary-300">Level {level}</span>
            <span className="text-surface-200">{totalXp} / {xpToNextLevel} XP</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-surface-700">
            <div
              className="h-full rounded-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all"
              style={{ width: `${Math.min((totalXp / xpToNextLevel) * 100, 100)}%` }}
            />
          </div>
          <div className="mt-2 flex items-center gap-3">
            <div className="flex items-center gap-1 text-xs text-warning">
              <Flame className="h-3 w-3" />
              <span>{currentStreak} day streak</span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-600/20 text-primary-300'
                    : 'text-surface-200 hover:bg-surface-800 hover:text-white',
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User section */}
        <div className="border-t border-surface-700 p-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary-600 text-sm font-bold">
              {user?.display_name?.charAt(0).toUpperCase() ?? '?'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="truncate text-sm font-medium text-white">
                {user?.display_name ?? 'Trader'}
              </p>
              <p className="truncate text-xs text-surface-200">
                Level {level}
              </p>
            </div>
            <button onClick={logout} className="text-surface-200 hover:text-danger" title="Logout">
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
