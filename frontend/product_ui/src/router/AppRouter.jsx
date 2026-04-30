import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import DashboardPage from '../pages/DashboardPage';
import TrendsPage from '../pages/TrendsPage';
import SkillLabDashboard from "../pages/SkillLabDashboard";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/trends" element={<TrendsPage />} />
          <Route path="/skilllab-dashboard" element={<SkillLabDashboard />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}