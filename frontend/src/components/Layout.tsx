import { useEffect } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../toast";
import type { StravaStatus } from "../types";

// Module-level flag: pull from Strava once per app load, not on every route.
let stravaSynced = false;

function todayISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

const icons = {
  calendar: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3.5" y="5" width="17" height="15.5" rx="2" />
      <path d="M3.5 9.5h17M8 3v4M16 3v4" />
      <path d="M8 13.5h.01M12 13.5h.01M16 13.5h.01M8 17h.01M12 17h.01" />
    </svg>
  ),
  progress: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M4 19h16" />
      <path d="M4 15l4-4 3 3 5-6 4 4" />
    </svg>
  ),
  plus: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden>
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
  profile: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c1.2-3.5 3.8-5 7-5s5.8 1.5 7 5" />
    </svg>
  ),
};

export default function Layout() {
  const { me } = useAuth();
  const toast = useToast();

  useEffect(() => {
    if (stravaSynced) return;
    stravaSynced = true;
    api<StravaStatus>("/api/integrations/strava")
      .then((s) =>
        s.connected
          ? api<{ imported: number }>("/api/integrations/strava/sync", { method: "POST" })
          : null,
      )
      .then((r) => {
        if (r && r.imported > 0) {
          toast(
            `${r.imported} ${r.imported === 1 ? "actividad importada" : "actividades importadas"} de Strava`,
          );
        }
      })
      .catch(() => {});
  }, [toast]);

  return (
    <div className="shell">
      <header className="topbar">
        <NavLink to="/" className="wordmark">
          Health<em>&amp;</em>Fitness
        </NavLink>
        {me?.user.avatar_url ? (
          <NavLink to="/perfil">
            <img className="avatar" src={me.user.avatar_url} alt="Tu perfil" referrerPolicy="no-referrer" />
          </NavLink>
        ) : null}
      </header>
      <main className="content">
        <Outlet />
      </main>
      <nav className="tabbar" aria-label="Navegación principal">
        <div className="tabbar-inner tabbar-4">
          <NavLink to="/" end className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
            {icons.calendar}
            <span>Calendario</span>
          </NavLink>
          <NavLink to="/progreso" className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
            {icons.progress}
            <span>Progreso</span>
          </NavLink>
          <NavLink
            to={`/dia/${todayISO()}?registro=1`}
            className={({ isActive }) => `tab tab-log${isActive ? " active" : ""}`}
          >
            <span className="tab-log-btn">{icons.plus}</span>
            <span>Registrar</span>
          </NavLink>
          <NavLink to="/perfil" className={({ isActive }) => `tab${isActive ? " active" : ""}`}>
            {icons.profile}
            <span>Perfil</span>
          </NavLink>
        </div>
      </nav>
    </div>
  );
}
