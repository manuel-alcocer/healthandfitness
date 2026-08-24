import { useEffect, useState } from "react";

import { api } from "../api";
import type { CalendarMonth } from "../types";

const MONTH_NAMES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];
const WEEKDAYS = ["L", "M", "X", "J", "V", "S", "D"];

function monthKey(year: number, month: number) {
  return `${year}-${String(month).padStart(2, "0")}`;
}

/** Month grid of compliance-colored days. Tapping a plannable day (from the
 * plan start on, past or future) hands its ISO date to `onSelectDay`. */
export default function MonthGrid({ onSelectDay }: { onSelectDay: (iso: string) => void }) {
  const now = new Date();
  const [cursor, setCursor] = useState({ year: now.getFullYear(), month: now.getMonth() + 1 });
  const [data, setData] = useState<CalendarMonth | null>(null);

  useEffect(() => {
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

  const firstWeekday = (new Date(data.year, data.month - 1, 1).getDay() + 6) % 7;
  const trackedFrom = data.tracked_from;

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
                day.level === "none" && plannable ? " future" : ""
              }`}
              disabled={!plannable && day.level === "none"}
              onClick={() => onSelectDay(day.date)}
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
    </div>
  );
}
