import { useEffect, useState } from "react";

import { api } from "../api";
import { ACTIVITY_LABELS, DAY_NAMES, type Plan } from "../types";

export default function PlanPage() {
  const [plan, setPlan] = useState<Plan | null>(null);
  const [missing, setMissing] = useState(false);
  const [tab, setTab] = useState<"comida" | "ejercicio">("comida");

  useEffect(() => {
    api<Plan>("/api/plan")
      .then(setPlan)
      .catch(() => setMissing(true));
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

  return (
    <div className="stack">
      <div className="card">
        <div className="eyebrow">Tu plan</div>
        <p style={{ margin: "6px 0 0" }}>{d.summary}</p>
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
          {d.nutrition.meals.map((meal) => (
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
          {d.exercise.weekly_schedule
            .slice()
            .sort((a, b) => a.day - b.day)
            .map((s, i) => (
              <div className={`session${s.type === "rest" ? " rest" : ""}`} key={i}>
                <span className="day">{DAY_NAMES[s.day - 1]}</span>
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
            ))}
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
