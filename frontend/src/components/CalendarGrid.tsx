import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import {
  ACTIVITY_LABELS,
  mealsForDate,
  type CalendarDay,
  type CalendarMonth,
  type Plan,
  type PlanSession,
} from "../types";

const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"];

function monthKey(year: number, month: number) {
  return `${year}-${String(month).padStart(2, "0")}`;
}

function sessionFor(plan: Plan | null, iso: string): PlanSession | null {
  if (!plan) return null;
  const jsDay = new Date(iso + "T00:00:00").getDay();
  const day = jsDay === 0 ? 7 : jsDay;
  return plan.data.exercise.weekly_schedule.find((s) => s.day === day) ?? null;
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

/** Compliance calendar + day planner: every day from the plan start on is
 * tappable and shows what the plan stipulates (session + meals), plus the
 * logged compliance on scored days. */
export default function CalendarGrid() {
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [data, setData] = useState<CalendarMonth | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [selected, setSelected] = useState<CalendarDay | null>(null);
  const [showMeals, setShowMeals] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api<Plan>("/api/plan").then(setPlan).catch(() => {});
  }, []);

  useEffect(() => {
    setSelected(null);
    setShowMeals(false);
    api<CalendarMonth>(`/api/calendar?month=${monthKey(cursor.year, cursor.month)}`)
      .then(setData)
      .catch(() => {});
  }, [cursor]);

  const shift = (delta: number) => {
    setCursor(({ year, month }) => {
      const d = new Date(year, month - 1 + delta, 1);
      return { year: d.getFullYear(), month: d.getMonth() + 1 };
    });
  };

  if (!data) return <p className="muted">Cargando calendario…</p>;

  // Monday-first offset for the 1st of the month.
  const firstWeekday = (new Date(data.year, data.month - 1, 1).getDay() + 6) % 7;
  const trackedFrom = data.tracked_from;
  const session = selected ? sessionFor(plan, selected.date) : null;
  const isPastOrToday = selected ? selected.date <= data.today : false;
  const selectedLabel = selected
    ? new Date(selected.date + "T00:00:00").toLocaleDateString("es-ES", {
        weekday: "long",
        day: "numeric",
        month: "long",
      })
    : "";

  return (
    <div>
      <div className="row-between" style={{ marginBottom: 8 }}>
        <button className="cal-nav" aria-label="Mes anterior" onClick={() => shift(-1)}>
          ‹
        </button>
        <strong>
          {MONTH_NAMES[data.month - 1]} {data.year}
          {data.medals > 0 && (
            <span className="muted" style={{ fontWeight: 500 }}>
              {" "}
              · {data.medals} 🏅
            </span>
          )}
        </strong>
        <button className="cal-nav" aria-label="Mes siguiente" onClick={() => shift(1)}>
          ›
        </button>
      </div>
      <div className="cal-grid" role="grid">
        {WEEKDAYS.map((d) => (
          <span key={d} className="cal-head">
            {d}
          </span>
        ))}
        {Array.from({ length: firstWeekday }).map((_, i) => (
          <span key={`pad${i}`} />
        ))}
        {data.days.map((day) => {
          const num = Number(day.date.slice(8));
          const isToday = day.date === data.today;
          const plannable = trackedFrom !== null && day.date >= trackedFrom;
          return (
            <button
              key={day.date}
              className={`cal-day lvl-${day.level}${isToday ? " today" : ""}${
                selected?.date === day.date ? " sel" : ""
              }${day.level === "none" && plannable ? " future" : ""}`}
              disabled={!plannable && day.level === "none"}
              onClick={() => setSelected(selected?.date === day.date ? null : day)}
              aria-label={`Día ${num}`}
            >
              {day.level === "medal" ? "🏅" : num}
            </button>
          );
        })}
      </div>
      <div className="legend-row" style={{ marginTop: 10 }}>
        <span className="key"><span className="dot lvl-red" /> Nada o poco</span>
        <span className="key"><span className="dot lvl-yellow" /> A medias</span>
        <span className="key"><span className="dot lvl-green" /> Casi todo</span>
        <span className="key">🏅 Todo o más</span>
      </div>

      {selected && (
        <div className="cal-detail">
          <div className="row-between">
            <strong>{selectedLabel}</strong>
            {selected.score != null && (
              <span className="mono muted">{Math.round(selected.score * 100)}%</span>
            )}
          </div>

          {/* What the plan stipulates for this day */}
          <div className="eyebrow" style={{ marginTop: 8 }}>
            Lo previsto
          </div>
          {session ? (
            session.type === "rest" ? (
              <p style={{ margin: "4px 0" }}>Descanso. También es parte del plan.</p>
            ) : (
              <p style={{ margin: "4px 0" }}>
                <strong>{session.title || ACTIVITY_LABELS[session.type]}</strong>{" "}
                <span className="chip plan" style={{ fontSize: 12 }}>
                  {ACTIVITY_LABELS[session.type]}
                </span>
                {session.target && (
                  <>
                    <br />
                    <span className="mono muted" style={{ fontSize: 13 }}>
                      {fmtTarget(session)}
                    </span>
                  </>
                )}
                {session.details && (
                  <>
                    <br />
                    <span className="muted" style={{ fontSize: 14 }}>{session.details}</span>
                  </>
                )}
              </p>
            )
          ) : (
            <p className="muted" style={{ margin: "4px 0" }}>Sin plan para este día.</p>
          )}

          {plan && (
            <>
              <button
                className="cal-meals-toggle"
                onClick={() => setShowMeals(!showMeals)}
                aria-expanded={showMeals}
              >
                {showMeals ? "▾" : "▸"} Comidas del día (
                {mealsForDate(plan.data, selected.date).length})
              </button>
              {showMeals && (
                <div style={{ marginTop: 4 }}>
                  {mealsForDate(plan.data, selected.date).map((meal) => (
                    <div key={meal.name} style={{ marginBottom: 8 }}>
                      <span className="meal-name" style={{ fontSize: 15 }}>
                        {meal.name}
                      </span>
                      {meal.time && <span className="meal-time"> · {meal.time}</span>}
                      <ul style={{ margin: "2px 0 0", paddingLeft: 18, color: "var(--ink-2)", fontSize: 14 }}>
                        {meal.options.map((option, i) => (
                          <li key={i}>{option}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}

          {/* What was actually logged (scored days only) */}
          {selected.level !== "none" && (
            <>
              <div className="eyebrow" style={{ marginTop: 8 }}>
                Lo registrado
              </div>
              <ul style={{ margin: "4px 0 8px", paddingLeft: 18, color: "var(--ink-2)" }}>
                <li>
                  Comidas:{" "}
                  {selected.nutrition_adherence != null
                    ? `${Math.round(selected.nutrition_adherence * 100)}% según plan`
                    : "sin registrar"}
                </li>
                {selected.planned ? (
                  <li>
                    {selected.planned}:{" "}
                    {selected.exercise_ratio != null && selected.exercise_ratio > 0
                      ? `${Math.round(selected.exercise_ratio * 100)}% del objetivo`
                      : "sin registrar"}
                  </li>
                ) : (
                  <li>Descanso{selected.activities ? " (¡y aun así entrenaste!)" : ""}</li>
                )}
              </ul>
            </>
          )}

          {isPastOrToday && selected.level !== "none" && (
            <button
              className="btn btn-secondary"
              onClick={() => navigate(`/registrar?tab=comidas&fecha=${selected.date}`)}
            >
              {selected.date === data.today ? "Registrar este día" : "Corregir este día"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
