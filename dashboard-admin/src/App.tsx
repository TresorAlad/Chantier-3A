import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import { AdminLayout } from './components/layout/AdminLayout';

// Pages
import { DashboardPage } from './pages/DashboardPage';
import { ParticipantsPage } from './pages/ParticipantsPage';
import { ParticipantDetailPage } from './pages/ParticipantDetailPage';
import { TicketsPage } from './pages/TicketsPage';
import { TicketTypesPage } from './pages/TicketTypesPage';
import { NexusNightPage } from './pages/NexusNightPage';
import { AdmissionsPage } from './pages/AdmissionsPage';
import { LoginPage } from './pages/LoginPage';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F8FAFC]">
        <div className="w-8 h-8 border-4 border-green-800 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      {/* ToastProvider doit englober AuthProvider */}
      <ToastProvider>
        <AuthProvider>
          <Routes>
            {/* Auth */}
            <Route path="/login" element={<LoginPage />} />

            {/* Dashboard Protected Application */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <AdminLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />

              <Route path="dashboard" element={<DashboardPage />} />

              <Route path="participants" element={<ParticipantsPage />} />
              <Route path="participants/:id" element={<ParticipantDetailPage />} />

              <Route path="tickets" element={<TicketsPage />} />
              <Route path="ticket-types" element={<TicketTypesPage />} />
              <Route path="nexus-night" element={<NexusNightPage />} />
              <Route path="admissions" element={<AdmissionsPage />} />

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Routes>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  );
};

export default App;
