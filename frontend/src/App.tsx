import { BrowserRouter, Navigate, Outlet, Route, Routes, useLocation } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth";
import Layout from "./components/Layout";
import CalendarPage from "./pages/CalendarPage";
import DayPage from "./pages/DayPage";
import HistoryPage from "./pages/HistoryPage";
import Login from "./pages/Login";
import Onboarding from "./pages/Onboarding";
import PlanPage from "./pages/PlanPage";
import ProfilePage from "./pages/ProfilePage";
import ProgressPage from "./pages/ProgressPage";
import Waiting from "./pages/Waiting";
import { ToastProvider } from "./toast";

function todayISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

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
                <Route path="/" element={<CalendarPage />} />
                <Route path="/dia/:fecha" element={<DayPage />} />
                <Route path="/espera" element={<Waiting />} />
                <Route path="/progreso" element={<ProgressPage />} />
                <Route path="/plan" element={<PlanPage />} />
                <Route path="/historial" element={<HistoryPage />} />
                <Route path="/perfil" element={<ProfilePage />} />
                {/* Old bookmark-friendly redirect */}
                <Route
                  path="/registrar"
                  element={<Navigate to={`/dia/${todayISO()}?registro=1`} replace />}
                />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}
