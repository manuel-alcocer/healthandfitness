import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import HistoryPage from "./pages/HistoryPage";
import LogPage from "./pages/LogPage";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import PlanPage from "./pages/PlanPage";
import ProfilePage from "./pages/ProfilePage";
import ProgressPage from "./pages/ProgressPage";
import Today from "./pages/Today";
import Waiting from "./pages/Waiting";
import { ToastProvider } from "./toast";

/** Routes users to the step of the journey they are in. */
function RequireAuth() {
  const { me, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="login-hero">
        <p className="muted">Cargando…</p>
      </div>
    );
  }
  if (!me) return <Navigate to="/login" replace />;

  const path = location.pathname;
  if (!me.profile && path !== "/onboarding") {
    return <Navigate to="/onboarding" replace />;
  }
  const goalStatus = me.goal?.status;
  const needsGoal = !me.goal || goalStatus === "cancelled" || goalStatus === "completed";
  if (me.profile && needsGoal && path !== "/onboarding") {
    return <Navigate to="/onboarding?paso=objetivo" replace />;
  }
  if (
    (goalStatus === "pending" || goalStatus === "suggested") &&
    path !== "/espera" &&
    path !== "/onboarding" &&
    path !== "/perfil"
  ) {
    return <Navigate to="/espera" replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<RequireAuth />}>
              <Route path="/onboarding" element={<Onboarding />} />
              <Route element={<Layout />}>
                <Route path="/" element={<Today />} />
                <Route path="/espera" element={<Waiting />} />
                <Route path="/progreso" element={<ProgressPage />} />
                <Route path="/registrar" element={<LogPage />} />
                <Route path="/plan" element={<PlanPage />} />
                <Route path="/historial" element={<HistoryPage />} />
                <Route path="/perfil" element={<ProfilePage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
