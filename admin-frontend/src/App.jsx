import React from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import AlternatesPage from './pages/AlternatesPage';
import AdmissionBatchesPage from './pages/AdmissionBatchesPage';
import AuditLogsPage from './pages/AuditLogsPage';
import DashboardLayout from './layouts/DashboardLayout';
import ChoicesPage from './pages/ChoicesPage';
import DashboardPage from './pages/DashboardPage';
import DoctorQuotasPage from './pages/DoctorQuotasPage';
import EnrollmentPage from './pages/EnrollmentPage';
import GiveupsPage from './pages/GiveupsPage';
import LoginPage from './pages/LoginPage';
import MasterQuotasPage from './pages/MasterQuotasPage';
import ProfessorHeatPage from './pages/ProfessorHeatPage';
import ProfessorsPage from './pages/ProfessorsPage';
import ReviewsPage from './pages/ReviewsPage';
import SelectionTimesPage from './pages/SelectionTimesPage';
import SharedQuotaPoolsPage from './pages/SharedQuotaPoolsPage';
import StudentsPage from './pages/StudentsPage';
import TokensPage from './pages/TokensPage';
import UsersPage from './pages/UsersPage';
import WeChatAccountsPage from './pages/WeChatAccountsPage';
import { getDashboardToken } from './utils/auth';


function ProtectedRoute({ children }) {
  return getDashboardToken() ? children : <Navigate to="/login" replace />;
}


export default function App() {
  const basename = import.meta.env.DEV ? '/' : '/dashboard';

  return (
    <BrowserRouter basename={basename}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="audit-logs" element={<AuditLogsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="professors" element={<ProfessorsPage />} />
          <Route path="students" element={<StudentsPage />} />
          <Route path="choices" element={<ChoicesPage />} />
          <Route path="professor-heat" element={<ProfessorHeatPage />} />
          <Route path="reviews" element={<ReviewsPage />} />
          <Route path="selection-times" element={<SelectionTimesPage />} />
          <Route path="admission-batches" element={<AdmissionBatchesPage />} />
          <Route path="enrollment" element={<EnrollmentPage />} />
          <Route path="master-quotas" element={<MasterQuotasPage />} />
          <Route path="doctor-quotas" element={<DoctorQuotasPage />} />
          <Route path="shared-quota-pools" element={<SharedQuotaPoolsPage />} />
          <Route path="wechat-accounts" element={<WeChatAccountsPage />} />
          <Route path="tokens" element={<TokensPage />} />
          <Route path="alternates" element={<AlternatesPage />} />
          <Route path="giveups" element={<GiveupsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
