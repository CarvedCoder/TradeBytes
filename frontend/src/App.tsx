import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import MainLayout from '@/layouts/MainLayout';
import AuthPage from '@/pages/AuthPage';
import DashboardPage from '@/pages/DashboardPage';
import SimulationPage from '@/pages/SimulationPage';
import PortfolioPage from '@/pages/PortfolioPage';
import NewsPage from '@/pages/NewsPage';
import LeaderboardPage from '@/pages/LeaderboardPage';
import LearningPage from '@/pages/LearningPage';
import CommunityPage from '@/pages/CommunityPage';
import AdvisorPage from '@/pages/AdvisorPage';

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/auth" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/auth" element={<AuthPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="simulation" element={<SimulationPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="news" element={<NewsPage />} />
        <Route path="leaderboard" element={<LeaderboardPage />} />
        <Route path="learning" element={<LearningPage />} />
        <Route path="community" element={<CommunityPage />} />
        <Route path="advisor" element={<AdvisorPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
