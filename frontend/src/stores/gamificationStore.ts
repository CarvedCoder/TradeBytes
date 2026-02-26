/**
 * Gamification Store - XP, streaks, badges, level state.
 */

import { create } from 'zustand';

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
  earned_at: string;
}

interface GamificationState {
  level: number;
  totalXp: number;
  xpToNextLevel: number;
  currentStreak: number;
  longestStreak: number;
  badges: Badge[];
  recentXpGain: number | null;

  setGamificationState: (state: Partial<GamificationState>) => void;
  addXp: (amount: number) => void;
  addBadge: (badge: Badge) => void;
  clearRecentXp: () => void;
}

export const useGamificationStore = create<GamificationState>()((set) => ({
  level: 1,
  totalXp: 0,
  xpToNextLevel: 100,
  currentStreak: 0,
  longestStreak: 0,
  badges: [],
  recentXpGain: null,

  setGamificationState: (state) => set(state),

  addXp: (amount) =>
    set((state) => ({
      totalXp: state.totalXp + amount,
      recentXpGain: amount,
    })),

  addBadge: (badge) =>
    set((state) => ({
      badges: [...state.badges, badge],
    })),

  clearRecentXp: () => set({ recentXpGain: null }),
}));
