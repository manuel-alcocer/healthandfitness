import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import VerdictStamp from "../components/VerdictStamp";
import { ACTIVITY_LABELS, type PlanData, type PlanSession, type Progress } from "../types";

function todayPlanSession(plan: PlanData | null): PlanSession | null {
  if (!plan) return null;
  const jsDay = new Date().getDay(); // 0=Sun..6=Sat
  const day = jsDay === 0 ? 7 : jsDay; // plan uses 1=Mon..7=Sun
  return plan.exercise.weekly_schedule.find((s) => s.day === day) ?? null;
}

function fmtTarget(session: PlanSession): string {
  const t = session.target ?? {};
  const parts: string[] = [];
  if (t.distance_km) parts.push(`${t.distance_km} km`);
  if (t.duration_min) parts.push(`${t.duration_min} min`);
  if (t.hr_zone) parts.push(`zona ${t.hr_zone}`);
  if (t.pace_min_km) parts.push(`${t.pace_min_km} min/km`);
  return parts.join(" · ");
}

export default function Today() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [plan, setPlan] = useState<PlanData | null>(null);

  useEffect(() => {
    api<Progress>("/api/progress").then(setProgress).catch(() => {});
    api<{ data: PlanData }>("/api/plan")
      .then((p) => setPlan(p.data))
      .catch(() => {});
  }, []);

  if (!progress) return <p className="muted">Cargando…</p>;

  const w = progress.weight;
  const ex = progress.exercise_week;
  const nut = progress.nutrition_week;
  const session = todayPlanSession(plan);
  const today = new Date().toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <div className="stack">
      {/* Verdict card — the coach's stamped logbook page */}
      <div className="card">
        <div className="row-between">
          <div className="eyebrow">{today}</div>
          {progress.verdict && <VerdictStamp status={progress.verdict.status} />}
        </div>
        <p style={{ marginBottom: 0 }}>{progress.verdict?.message}</p>
      </div>

      {/* Weight hero */}
      <div className="card">
        <div className="eyebrow">Peso actual (media 7 días)</div>
        <div className="row-between">
          <div className="big-number">
            {w?.current_kg != null ? w.current_kg.toFixed(1) : "—"}
            <small>kg</small>
          </div>
          {w?.delta_kg != null && (
            <span className={`chip ${w.status === "behind" ? "bad" : "good"}`}>
              {w.delta_kg > 0 ? "▲" : "▼"} {Math.abs(w.delta_kg).toFixed(1)} kg vs plan
            </span>
          )}
        </div>
        <div className="legend-row" style={{ marginTop: 8 }}>
          {w?.lost_kg != null && (
            <span>
              Perdidos <strong className="mono">{w.lost_kg.toFixed(1)} kg</strong>
            </span>
          )}
          {w?.to_go_kg != null && (
            <span>
              Te quedan <strong className="mono">{Math.max(0, w.to_go_kg).toFixed(1)} kg</strong>
            </span>
          )}
          {progress.streak_days ? (
            <span>
              Racha <strong className="mono">{progress.streak_days} días</strong>
            </span>
          ) : null}
        </div>
      </div>

      {/* This week */}
      {ex && (
        <div className="card">
          <div className="row-between">
            <div className="eyebrow">Esta semana</div>
            <span className="mono muted" style={{ fontSize: 12 }}>
              {ex.sessions_done}/{ex.sessions_planned} sesiones
            </span>
          </div>
          <div className="weekbar" style={{ margin: "10px 0" }} aria-hidden>
            {Array.from({ length: Math.max(ex.sessions_planned, 1) }).map((_, i) => (
              <span key={i} className={i < ex.sessions_done ? "done" : ""} />
            ))}
          </div>
          <div className="legend-row">
            <span>
              <strong className="mono">{ex.distance_done_km}</strong>
              {ex.distance_planned_km ? (
                <span className="muted"> / {ex.distance_planned_km} km</span>
              ) : (
                <span className="muted"> km</span>
              )}
            </span>
            <span>
              <strong className="mono">{ex.minutes_done}</strong>
              <span className="muted"> min</span>
            </span>
            {nut?.adherence != null && (
              <span>
                Comidas <strong className="mono">{Math.round(nut.adherence * 100)}%</strong>
              </span>
            )}
          </div>
        </div>
      )}

      {/* Today's planned session */}
      {session && (
        <div className="card">
          <div className="eyebrow">Hoy toca</div>
          {session.type === "rest" ? (
            <>
              <h2>Descanso</h2>
              <p className="muted" style={{ marginBottom: 0 }}>
                Recupera. El descanso también es parte del plan.
              </p>
            </>
          ) : (
            <>
              <h2>
                {session.title || ACTIVITY_LABELS[session.type]}{" "}
                <span className="chip plan">{ACTIVITY_LABELS[session.type]}</span>
              </h2>
              {session.target && <p className="mono muted">{fmtTarget(session)}</p>}
              {session.details && <p className="muted">{session.details}</p>}
              <Link
                className="btn btn-primary"
                to={`/registrar?tab=actividad&tipo=${session.type}&plan_day=${session.day}`}
              >
                Registrar esta sesión
              </Link>
            </>
          )}
        </div>
      )}

      <div className="btn-row">
        <Link className="btn btn-secondary" to="/registrar?tab=peso">
          Pesarme
        </Link>
        <Link className="btn btn-secondary" to="/registrar?tab=comidas">
          Comidas de hoy
        </Link>
      </div>
    </div>
  );
}
