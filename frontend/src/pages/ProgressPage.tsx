import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";
import CalendarGrid from "../components/CalendarGrid";
import VolumeChart from "../components/VolumeChart";
import WeightChart from "../components/WeightChart";
import type { Progress } from "../types";

export default function ProgressPage() {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [metric, setMetric] = useState<"distance_km" | "minutes">("distance_km");

  useEffect(() => {
    api<Progress>("/api/progress").then(setProgress).catch(() => {});
  }, []);

  if (!progress) return <p className="muted">Cargando…</p>;
  if (progress.state !== "active") {
    return (
      <div className="card waiting">
        <h2>Aún no hay progreso que mostrar</h2>
        <p className="muted">Cuando tu plan esté activo, aquí verás tu evolución.</p>
      </div>
    );
  }

  const weeks = progress.weekly_exercise ?? [];
  const anyExercise = weeks.some((w) => w.sessions > 0);

  return (
    <div className="stack">
      <h2 className="section-title">Tu calendario</h2>
      <div className="card">
        <CalendarGrid />
      </div>

      <h2 className="section-title">Evolución del peso</h2>
      <div className="card chart-card">
        {progress.weight_series?.length ? (
          <WeightChart
            real={progress.weight_series}
            expected={progress.expected_series ?? []}
          />
        ) : (
          <p className="muted" style={{ margin: 0 }}>
            Todavía no hay pesajes. <Link to="/registrar?tab=peso">Registra el primero</Link> para
            ver tu curva junto a la prevista por el plan.
          </p>
        )}
      </div>

      <div className="tiles">
        <div className="tile">
          <div className="eyebrow">Perdido</div>
          <div className="value">
            {progress.weight?.lost_kg != null ? progress.weight.lost_kg.toFixed(1) : "—"}
            <small> kg</small>
          </div>
        </div>
        <div className="tile">
          <div className="eyebrow">Hasta el objetivo</div>
          <div className="value">
            {progress.weight?.to_go_kg != null
              ? Math.max(0, progress.weight.to_go_kg).toFixed(1)
              : "—"}
            <small> kg</small>
          </div>
        </div>
      </div>

      <div className="row-between">
        <h2 className="section-title">Ejercicio semanal</h2>
        <div className="segmented" style={{ width: 150 }}>
          <button className={metric === "distance_km" ? "on" : ""} onClick={() => setMetric("distance_km")}>
            km
          </button>
          <button className={metric === "minutes" ? "on" : ""} onClick={() => setMetric("minutes")}>
            min
          </button>
        </div>
      </div>
      <div className="card chart-card">
        {anyExercise ? (
          <VolumeChart weeks={weeks} metric={metric} />
        ) : (
          <p className="muted" style={{ margin: 0 }}>
            Sin actividades registradas todavía.{" "}
            <Link to="/registrar?tab=actividad">Registra tu primera sesión</Link>.
          </p>
        )}
      </div>

      <Link className="btn btn-ghost" to="/historial">
        Ver historial completo
      </Link>
    </div>
  );
}
