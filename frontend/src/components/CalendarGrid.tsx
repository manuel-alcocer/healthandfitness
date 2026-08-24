import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../api";
import type { CalendarDay, CalendarMonth } from "../types";

const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"];

function monthKey(year: number, month: number) {
  return `${year}-${String(month).padStart(2, "0")}`;
}

/** The compliance calendar: one colored cell per day, medal for perfect days. */
export default function CalendarGrid() {
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [data, setData] = useState<CalendarMonth | null>(null);
  const [selected, setSelected] = useState<CalendarDay | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setSelected(null);
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
  const isCurrentMonth =
    cursor.year === now.getFullYear() && cursor.month === now.getMonth() + 1;

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
        <button
          className="cal-nav"
          aria-label="Mes siguiente"
          onClick={() => shift(1)}
          disabled={isCurrentMonth}
        >
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
          return (
            <button
              key={day.date}
              className={`cal-day lvl-${day.level}${isToday ? " today" : ""}${
                selected?.date === day.date ? " sel" : ""
              }`}
              disabled={day.level === "none"}
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
            <strong>
              {new Date(selected.date + "T00:00:00").toLocaleDateString("es-ES", {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </strong>
            {selected.score != null && (
              <span className="mono muted">{Math.round(selected.score * 100)}%</span>
            )}
          </div>
          <ul style={{ margin: "6px 0", paddingLeft: 18, color: "var(--ink-2)" }}>
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
              <li>Día de descanso{selected.activities ? " (¡y aun así entrenaste!)" : ""}</li>
            )}
          </ul>
          <button
            className="btn btn-secondary"
            onClick={() => navigate(`/registrar?tab=comidas&fecha=${selected.date}`)}
          >
            Corregir este día
          </button>
        </div>
      )}
    </div>
  );
}
