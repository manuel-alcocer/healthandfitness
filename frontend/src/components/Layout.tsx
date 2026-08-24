import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth";

const icons = {
  today: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 11.5 12 4l9 7.5" />
      <path d="M5.5 10.5V20h13v-9.5" />
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
  plan: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="5" y="3.5" width="14" height="17" rx="2" />
      <path d="M9 8h6M9 12h6M9 16h4" />
    </svg>
  ),
  profile: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden>
      <circle cx="12" cy="8" r="3.5" />
      <path d="M5 20c1.2-3.5 3.8-5 7-5s5.8 1.5 7 5" />
    </svg>
  ),
};

function Tab({
  to,
  label,
  icon,
}: {
  to: string;
  label: string;
  icon: keyof typeof icons;
}) {
  return (
    <NavLink to={to} className={({ isActive }) => `tab${isActive ? " active" : ""}`} end={to === "/"}>
      {icons[icon]}
      <span>{label}</span>
    </NavLink>
  );
}

export default function Layout() {
  const { me } = useAuth();
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
        <div className="tabbar-inner">
          <Tab to="/" label="Hoy" icon="today" />
          <Tab to="/progreso" label="Progreso" icon="progress" />
          <NavLink
            to="/registrar"
            className={({ isActive }) => `tab tab-log${isActive ? " active" : ""}`}
          >
            <span className="tab-log-btn">{icons.plus}</span>
            <span>Registrar</span>
          </NavLink>
          <Tab to="/plan" label="Plan" icon="plan" />
          <Tab to="/perfil" label="Perfil" icon="profile" />
        </div>
      </nav>
    </div>
  );
}
