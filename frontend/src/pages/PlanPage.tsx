import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";
import {
  ACTIVITY_LABELS,
  DAY_NAMES,
  planDayOf,
  type Plan,
  type PlanDayData,
} from "../types";

function todayISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

function shiftDate(iso: string, days: number) {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + days);
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

/** "LUN 31" — the tab label for a concrete date. */
function dayLabel(iso: string) {
  return `${DAY_NAMES[planDayOf(iso) - 1]} ${Number(iso.slice(8, 10))}`;
}

export default function PlanPage() {
  const { me } = useAuth();
  const [plan, setPlan] = useState<Plan | null>(null);
  const [days, setDays] = useState<PlanDayData[]>([]);
  const [missing, setMissing] = useState(false);
  const [tab, setTab] = useState<"comida" | "ejercicio">("comida");
  const [menuDate, setMenuDate] = useState(todayISO());

  useEffect(() => {
    api<Plan>("/api/plan")
      .then(setPlan)
      .catch(() => setMissing(true));
    // The plan is day-by-day: show the coming 7 real dates, not a repeating
    // weekly template.
    const from = todayISO();
    api<{ results: PlanDayData[] }>(`/api/plan/days?from=${from}&to=${shiftDate(from, 6)}`)
      .then((r) => setDays(r.results))
      .catch(() => {});
  }, []);

  if (missing)
    return (
      <div className="card waiting">
        <h2>Tu plan aún no está listo</h2>
        <p className="muted">En cuanto tu entrenador lo prepare aparecerá aquí.</p>
      </div>
    );
  if (!plan) return <p className="muted">Cargando…</p>;

  const d = plan.data;
  const selected = days.find((x) => x.date === menuDate) ?? days[0];

  return (
    <div className="stack">
      <div className="card">
        <div className="row-between">
          <div className="eyebrow">Tu plan</div>
          {me?.goal?.revision_requested && (
            <span className="chip plan">Actualización pedida</span>
          )}
        </div>
        <p style={{ margin: "6px 0 0" }}>{d.summary}</p>
        {!me?.goal?.revision_requested && (
          <p className="hint muted" style={{ margin: "8px 0 0" }}>
            ¿Ya no te encaja el ejercicio? Pide una actualización desde{" "}
            <Link to="/perfil">tu perfil</Link>.
          </p>
        )}
      </div>

      <div className="tiles">
        <div className="tile">
          <div className="eyebrow">Calorías diarias</div>
          <div className="value">
            {d.daily_calories}
            <small> kcal</small>
          </div>
        </div>
        <div className="tile">
          <div className="eyebrow">Proteína · HC · Grasa</div>
          <div className="value" style={{ fontSize: 22 }}>
            <span className="mono">
              {d.macros.protein_g}/{d.macros.carbs_g}/{d.macros.fat_g}
            </span>
            <small> g</small>
          </div>
        </div>
      </div>

      <div className="segmented">
        <button className={tab === "comida" ? "on" : ""} onClick={() => setTab("comida")}>
          Alimentación
        </button>
        <button className={tab === "ejercicio" ? "on" : ""} onClick={() => setTab("ejercicio")}>
          Ejercicio
        </button>
      </div>

      {tab === "comida" ? (
        <div className="card">
          {days.length > 1 && (
            <div className="day-select" role="tablist" aria-label="Próximos días">
              {days.map((day) => (
                <button
                  key={day.date}
                  role="tab"
                  aria-selected={selected?.date === day.date}
                  className={selected?.date === day.date ? "on" : ""}
                  onClick={() => setMenuDate(day.date)}
                >
                  {dayLabel(day.date)}
                </button>
              ))}
            </div>
          )}
          {(selected?.meals ?? []).map((meal) => (
            <div className="meal-row" key={meal.name}>
              <div className="row-between">
                <span className="meal-name">{meal.name}</span>
                {meal.time && <span className="meal-time">{meal.time}</span>}
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, color: "var(--ink-2)" }}>
                {meal.options.map((option, i) => (
                  <li key={i}>{option}</li>
                ))}
              </ul>
            </div>
          ))}
          {d.nutrition.guidelines?.length ? (
            <>
              <hr className="divider" />
              <div className="eyebrow">Pautas</div>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "var(--ink-2)" }}>
                {d.nutrition.guidelines.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      ) : (
        <div className="card">
          {days.map((day) => {
            const s = day.session;
            return (
              <div className={`session${s.type === "rest" ? " rest" : ""}`} key={day.date}>
                <span className="day">
                  <Link to={`/dia/${day.date}`} style={{ color: "inherit", textDecoration: "none" }}>
                    {dayLabel(day.date)}
                  </Link>
                </span>
                <div style={{ flex: 1 }}>
                  <div className="row-between">
                    <strong>{s.title || ACTIVITY_LABELS[s.type]}</strong>
                    <span className="chip plan" style={{ fontSize: 12 }}>
                      {ACTIVITY_LABELS[s.type]}
                    </span>
                  </div>
                  {s.target && (
                    <div className="targets">
                      {s.target.distance_km && <span>{s.target.distance_km} km</span>}
                      {s.target.duration_min && <span>{s.target.duration_min} min</span>}
                      {s.target.hr_zone && <span>zona {s.target.hr_zone}</span>}
                      {s.target.pace_min_km && <span>{s.target.pace_min_km} min/km</span>}
                    </div>
                  )}
                  {s.details && <p className="muted" style={{ margin: "4px 0 0", fontSize: 14 }}>{s.details}</p>}
                </div>
              </div>
            );
          })}
          {d.exercise.guidelines?.length ? (
            <>
              <hr className="divider" />
              <div className="eyebrow">Pautas</div>
              <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "var(--ink-2)" }}>
                {d.exercise.guidelines.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}
