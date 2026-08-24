import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "../auth";
import { ACTIVITY_LABELS } from "../types";

const ACTIVITY_LEVEL_LABELS: Record<string, string> = {
  sedentary: "Sedentario",
  light: "Ligera",
  moderate: "Moderada",
  active: "Activa",
  very_active: "Muy activa",
};

function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso + "T00:00:00").toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function ProfilePage() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  if (!me) return null;
  const { user, profile, goal } = me;

  return (
    <div className="stack">
      <div className="card row-between">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {user.avatar_url && (
            <img className="avatar" src={user.avatar_url} alt="" referrerPolicy="no-referrer" style={{ width: 48, height: 48 }} />
          )}
          <div>
            <strong>
              {user.first_name} {user.last_name}
            </strong>
            <div className="muted" style={{ fontSize: 14 }}>
              {user.email}
            </div>
          </div>
        </div>
      </div>

      {profile && (
        <div className="card">
          <div className="row-between">
            <div className="eyebrow">Tus datos</div>
            <Link to="/onboarding" className="muted" style={{ fontSize: 14 }}>
              Editar
            </Link>
          </div>
          <div className="tiles" style={{ marginTop: 10 }}>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">Edad · Altura</div>
              <div className="mono">
                {profile.age} años · {profile.height_cm} cm
              </div>
            </div>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">IMC inicial</div>
              <div className="mono">{profile.bmi}</div>
            </div>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">Actividad</div>
              <div>{ACTIVITY_LEVEL_LABELS[profile.activity_level]}</div>
            </div>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">Te gusta</div>
              <div>
                {profile.preferred_activities.map((a) => ACTIVITY_LABELS[a]).join(", ") || "—"}
              </div>
            </div>
          </div>
        </div>
      )}

      {goal && (
        <div className="card">
          <div className="eyebrow">Objetivo</div>
          <div className="big-number" style={{ fontSize: 40 }}>
            {parseFloat(goal.target_weight_kg)}
            <small>kg</small>
          </div>
          <p className="muted" style={{ margin: "4px 0 0" }}>
            Para el {fmtDate(goal.target_date)} · empezaste en{" "}
            {parseFloat(goal.start_weight_kg)} kg
          </p>
          {goal.admin_message && goal.status === "active" && (
            <>
              <hr className="divider" />
              <div className="eyebrow">Mensaje de tu entrenador</div>
              <p style={{ margin: "4px 0 0" }}>{goal.admin_message}</p>
            </>
          )}
        </div>
      )}

      <button
        className="btn btn-ghost"
        onClick={() => {
          logout();
          navigate("/login");
        }}
      >
        Cerrar sesión
      </button>
    </div>
  );
}
