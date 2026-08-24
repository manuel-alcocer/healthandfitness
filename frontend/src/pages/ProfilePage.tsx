import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import { useToast } from "../toast";
import { ACTIVITY_LABELS } from "../types";

const REVISION_ACTIVITIES = ["walk", "run", "swim", "bike", "gym", "hike"];

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
  const { me, logout, refreshMe } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [editingPlan, setEditingPlan] = useState(false);
  const [activities, setActivities] = useState<string[]>(me?.profile?.preferred_activities ?? []);
  const [days, setDays] = useState(String(me?.profile?.training_days_per_week ?? 3));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  if (!me) return null;
  const { user, profile, goal } = me;

  async function requestRevision() {
    setBusy(true);
    try {
      await api("/api/auth/profile", {
        method: "PUT",
        body: { preferred_activities: activities, training_days_per_week: parseInt(days) },
      });
      await api("/api/goal/request-revision", { method: "POST", body: { note } });
      await refreshMe();
      setEditingPlan(false);
      toast("Petición enviada a tu entrenador");
    } catch {
      toast("No se pudo enviar la petición");
    } finally {
      setBusy(false);
    }
  }

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
          {goal.status === "active" && (
            <Link className="btn btn-ghost" style={{ marginTop: 12 }} to="/plan">
              Ver plan completo
            </Link>
          )}
        </div>
      )}

      {goal?.status === "active" && (
        <div className="card">
          <div className="eyebrow">Tu plan de ejercicio</div>
          {goal.revision_requested ? (
            <p style={{ margin: "6px 0 0" }}>
              <span className="chip plan">Actualización pedida</span>{" "}
              Tu entrenador está preparando el plan actualizado. Mientras tanto sigue con el
              actual.
            </p>
          ) : editingPlan ? (
            <>
              <p className="muted">
                Marca el ejercicio que estás dispuesto a hacer a partir de ahora y cuéntanos por
                qué. Tu entrenador te preparará un plan actualizado.
              </p>
              <div className="field">
                <label>Ejercicio que quiero hacer</label>
                <div className="chip-select">
                  {REVISION_ACTIVITIES.map((a) => (
                    <button
                      key={a}
                      type="button"
                      className={activities.includes(a) ? "on" : ""}
                      onClick={() =>
                        setActivities((cur) =>
                          cur.includes(a) ? cur.filter((x) => x !== a) : [...cur, a],
                        )
                      }
                    >
                      {ACTIVITY_LABELS[a]}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <label htmlFor="rev-days">Días por semana</label>
                <input
                  id="rev-days"
                  type="number"
                  min={1}
                  max={7}
                  inputMode="numeric"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="rev-note">Cuéntale a tu entrenador (opcional)</label>
                <textarea
                  id="rev-note"
                  rows={2}
                  placeholder="Me he apuntado a la piscina, me duele la rodilla al correr…"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>
              <div className="btn-row">
                <button className="btn btn-ghost" onClick={() => setEditingPlan(false)}>
                  Cancelar
                </button>
                <button
                  className="btn btn-primary"
                  disabled={busy || activities.length === 0}
                  onClick={requestRevision}
                >
                  Pedir plan actualizado
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="muted" style={{ margin: "6px 0 10px" }}>
                ¿Has cambiado de ejercicio o de disponibilidad? Pide a tu entrenador un plan
                actualizado.
              </p>
              <button className="btn btn-secondary" onClick={() => setEditingPlan(true)}>
                Cambiar mi ejercicio y pedir actualización
              </button>
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
