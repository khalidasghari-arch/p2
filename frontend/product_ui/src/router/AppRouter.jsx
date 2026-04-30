import { BrowserRouter, Routes, Route } from 'react-router-dom';
import AppLayout from '../components/layout/AppLayout';
import DashboardPage from '../pages/DashboardPage';
import TrendsPage from '../pages/TrendsPage';
import SkillLabDashboard from "../pages/SkillLabDashboard";
import HomePage from "../pages/HomePage";

export default function AppRouter() {
  return (
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/skilllab-dashboard" element={<SkillLabDashboard />} />
          <Route path="/trends" element={<TrendsPage />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  );
}