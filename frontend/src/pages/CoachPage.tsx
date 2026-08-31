import { useEffect, useState } from "react";

import { api } from "../api";
import type { WeeklyFeedback } from "../types";

const MONTHS = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

/** "Semana del 24 al 30 de agosto" (or spanning two months). */
function weekRange(weekStart: string) {
  const start = new Date(weekStart + "T00:00:00");
  const end = new Date(start);
  end.setDate(end.getDate() + 6);
  const sameMonth = start.getMonth() === end.getMonth();
  const from = sameMonth
    ? String(start.getDate())
    : `${start.getDate()} de ${MONTHS[start.getMonth()]}`;
  return `Semana del ${from} al ${end.getDate()} de ${MONTHS[end.getMonth()]}`;
}

/** The stat chips a review can carry; unknown keys are simply not shown. */
const STAT_FORMATS: [string, string, (v: number) => string][] = [
  ["weight_delta_kg", "Peso", (v) => `${v > 0 ? "+" : ""}${v.toLocaleString("es-ES")} kg`],
  ["distance_km", "Distancia", (v) => `${v.toLocaleString("es-ES")} km`],
  ["active_days", "Días activos", (v) => `${v}/7`],
  ["nutrition_adherence", "Menú cumplido", (v) => `${Math.round(v * 100)} %`],
];

export default function CoachPage() {
  const [feedback, setFeedback] = useState<WeeklyFeedback[] | null>(null);

  useEffect(() => {
    api<{ results: WeeklyFeedback[] }>("/api/feedback")
      .then((r) => setFeedback(r.results))
      .catch(() => setFeedback([]));
  }, []);

  if (feedback === null) return <p className="muted">Cargando…</p>;

  if (!feedback.length)
    return (
      <div className="card waiting">
        <h2>Aún no hay resúmenes</h2>
        <p className="muted">
          Cada semana tu entrenador revisará tus datos y publicará aquí su resumen:
          qué tal ha ido, y qué ajusta en tu plan para la siguiente.
        </p>
      </div>
    );

  return (
    <div className="stack">
      <div className="eyebrow" style={{ marginTop: 4 }}>Resumen semanal de tu entrenador</div>
      {feedback.map((fb) => {
        const stats = STAT_FORMATS.filter(([key]) => typeof fb.stats?.[key] === "number");
        return (
          <div className="card" key={fb.week_start}>
            <div className="eyebrow">{weekRange(fb.week_start)}</div>
            {stats.length > 0 && (
              <div className="tiles" style={{ margin: "10px 0" }}>
                {stats.map(([key, label, fmt]) => (
                  <div className="tile" key={key}>
                    <div className="eyebrow">{label}</div>
                    <div className="value" style={{ fontSize: 20 }}>
                      {fmt(fb.stats[key] as number)}
                    </div>
                  </div>
                ))}
              </div>
            )}
            {fb.summary.split(/\n\n+/).map((paragraph, i) => (
              <p key={i} style={{ margin: i === 0 ? "6px 0 0" : "10px 0 0" }}>
                {paragraph}
              </p>
            ))}
            {fb.adjustments.length > 0 && (
              <>
                <hr className="divider" />
                <div className="eyebrow">Cambios aplicados en tu plan</div>
                <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "var(--ink-2)" }}>
                  {fb.adjustments.map((adj, i) => (
                    <li key={i}>{adj}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
