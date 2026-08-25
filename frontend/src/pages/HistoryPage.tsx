import { useCallback, useEffect, useState } from "react";

import { api } from "../api";
import { useToast } from "../toast";
import {
  ACTIVITY_LABELS,
  type ActivityEntry,
  type NutritionEntry,
  type WeightEntry,
} from "../types";

type Kind = "peso" | "actividad" | "comidas";

function fmt(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
  });
}

export default function HistoryPage() {
  const [kind, setKind] = useState<Kind>("peso");
  const [weights, setWeights] = useState<WeightEntry[]>([]);
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [nutrition, setNutrition] = useState<NutritionEntry[]>([]);
  const toast = useToast();

  const load = useCallback(() => {
    api<{ results: WeightEntry[] }>("/api/tracking/weights?limit=100").then((r) =>
      setWeights(r.results),
    );
    api<{ results: ActivityEntry[] }>("/api/tracking/activities?limit=100").then((r) =>
      setActivities(r.results),
    );
    api<{ results: NutritionEntry[] }>("/api/tracking/nutrition?limit=100").then((r) =>
      setNutrition(r.results),
    );
  }, []);

  useEffect(load, [load]);

  async function remove(path: string) {
    await api(path, { method: "DELETE" });
    toast("Registro eliminado");
    load();
  }

  const del = (path: string) => (
    <button className="del" aria-label="Eliminar registro" onClick={() => remove(path)}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3" />
      </svg>
    </button>
  );

  return (
    <div className="stack">
      <h2 className="section-title">Historial</h2>
      <div className="segmented">
        {(["peso", "actividad", "comidas"] as const).map((k) => (
          <button key={k} className={kind === k ? "on" : ""} onClick={() => setKind(k)}>
            {k === "peso" ? "Peso" : k === "actividad" ? "Actividad" : "Comidas"}
          </button>
        ))}
      </div>
      <div className="card">
        {kind === "peso" &&
          (weights.length ? (
            weights.map((e) => (
              <div className="entry-row" key={e.id}>
                <span className="when">{fmt(e.date)}</span>
                <span className="what">
                  <strong className="mono">{parseFloat(e.weight_kg).toFixed(1)} kg</strong>
                  {e.body_fat_pct && (
                    <span className="muted mono"> · {e.body_fat_pct}% graso</span>
                  )}
                  {e.notes && <span className="muted"> — {e.notes}</span>}
                </span>
                {del(`/api/tracking/weights/${e.id}`)}
              </div>
            ))
          ) : (
            <p className="muted" style={{ margin: 0 }}>Sin pesajes todavía.</p>
          ))}

        {kind === "actividad" &&
          (activities.length ? (
            activities.map((e) => (
              <div className="entry-row" key={e.id}>
                <span className="when">{fmt(e.date)}</span>
                <span className="what">
                  <strong>{e.title || ACTIVITY_LABELS[e.activity_type]}</strong>
                  {e.source === "strava" && (
                    <span className="chip strava" style={{ fontSize: 11, marginLeft: 6 }}>
                      Strava
                    </span>
                  )}
                  <span className="muted mono">
                    {" "}
                    · {e.duration_min} min
                    {e.distance_km && ` · ${parseFloat(e.distance_km)} km`}
                    {e.avg_hr && ` · ${e.avg_hr} ppm`}
                  </span>
                </span>
                {del(`/api/tracking/activities/${e.id}`)}
              </div>
            ))
          ) : (
            <p className="muted" style={{ margin: 0 }}>Sin actividades todavía.</p>
          ))}

        {kind === "comidas" &&
          (nutrition.length ? (
            nutrition.map((e) => (
              <div className="entry-row" key={e.id}>
                <span className="when">{fmt(e.date)}</span>
                <span className="what">
                  <strong className="mono">
                    {e.adherence != null ? `${Math.round(e.adherence * 100)}%` : "—"}
                  </strong>
                  <span className="muted"> según plan</span>
                  {e.water_l && <span className="muted mono"> · {e.water_l} L agua</span>}
                </span>
                {del(`/api/tracking/nutrition/${e.id}`)}
              </div>
            ))
          ) : (
            <p className="muted" style={{ margin: 0 }}>Sin registros de comidas todavía.</p>
          ))}
      </div>
    </div>
  );
}
