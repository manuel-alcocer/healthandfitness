import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api";
import { useToast } from "../toast";
import { ACTIVITY_LABELS, type NutritionEntry, type Plan } from "../types";

type Tab = "peso" | "actividad" | "comidas";

const ACTIVITY_OPTIONS = ["walk", "run", "swim", "bike", "gym", "hike", "other"];

function todayISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

export default function LogPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const initialTab = (params.get("tab") as Tab) || "peso";
  const [tab, setTab] = useState<Tab>(initialTab);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // --- Weight form ---
  const [weight, setWeight] = useState({ date: todayISO(), weight_kg: "", body_fat_pct: "", notes: "" });

  // --- Activity form ---
  const [activity, setActivity] = useState({
    date: todayISO(),
    activity_type: params.get("tipo") || "walk",
    title: "",
    duration_min: "",
    distance_km: "",
    avg_hr: "",
    max_hr: "",
    calories: "",
    perceived_effort: "",
    plan_day: params.get("plan_day") || "",
    notes: "",
  });

  const avgSpeed = useMemo(() => {
    const dist = parseFloat(activity.distance_km);
    const dur = parseFloat(activity.duration_min);
    if (!dist || !dur) return null;
    return dist / (dur / 60);
  }, [activity.distance_km, activity.duration_min]);

  const pace = useMemo(() => {
    const dist = parseFloat(activity.distance_km);
    const dur = parseFloat(activity.duration_min);
    if (!dist || !dur) return null;
    const minPerKm = dur / dist;
    const min = Math.floor(minPerKm);
    const sec = Math.round((minPerKm - min) * 60);
    return `${min}:${sec.toString().padStart(2, "0")}`;
  }, [activity.distance_km, activity.duration_min]);

  // --- Nutrition form (from the plan's meals) ---
  const [plan, setPlan] = useState<Plan | null>(null);
  const [mealStatus, setMealStatus] = useState<Record<string, "full" | "partial" | "skipped">>({});
  const [water, setWater] = useState("");
  const [nutritionNotes, setNutritionNotes] = useState("");

  useEffect(() => {
    api<Plan>("/api/plan").then(setPlan).catch(() => {});
    // Preload today's nutrition entry so re-editing is natural.
    api<{ results: NutritionEntry[] }>(`/api/tracking/nutrition?limit=50`)
      .then((r) => {
        const today = r.results.find((e) => e.date === todayISO());
        if (today) {
          const map: Record<string, "full" | "partial" | "skipped"> = {};
          today.meals.forEach((m) => (map[m.name] = m.status));
          setMealStatus(map);
          if (today.water_l) setWater(today.water_l);
          setNutritionNotes(today.notes);
        }
      })
      .catch(() => {});
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (tab === "peso") {
        await api("/api/tracking/weights", {
          method: "POST",
          body: {
            date: weight.date,
            weight_kg: weight.weight_kg,
            body_fat_pct: weight.body_fat_pct || null,
            notes: weight.notes,
          },
        });
        toast("Peso registrado");
      } else if (tab === "actividad") {
        await api("/api/tracking/activities", {
          method: "POST",
          body: {
            date: activity.date,
            activity_type: activity.activity_type,
            title: activity.title,
            duration_min: parseInt(activity.duration_min),
            distance_km: activity.distance_km || null,
            avg_hr: activity.avg_hr ? parseInt(activity.avg_hr) : null,
            max_hr: activity.max_hr ? parseInt(activity.max_hr) : null,
            avg_speed_kmh: avgSpeed ? avgSpeed.toFixed(2) : null,
            calories: activity.calories ? parseInt(activity.calories) : null,
            perceived_effort: activity.perceived_effort ? parseInt(activity.perceived_effort) : null,
            plan_day: activity.plan_day ? parseInt(activity.plan_day) : null,
            notes: activity.notes,
          },
        });
        toast("Actividad registrada");
      } else {
        const meals = (plan?.data.nutrition.meals ?? []).map((m) => ({
          name: m.name,
          status: mealStatus[m.name] ?? "skipped",
        }));
        await api("/api/tracking/nutrition", {
          method: "POST",
          body: { date: todayISO(), meals, water_l: water || null, notes: nutritionNotes },
        });
        toast("Comidas registradas");
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar. Revisa los campos.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="segmented">
        {(["peso", "actividad", "comidas"] as const).map((t) => (
          <button key={t} className={tab === t ? "on" : ""} onClick={() => setTab(t)}>
            {t === "peso" ? "Peso" : t === "actividad" ? "Actividad" : "Comidas"}
          </button>
        ))}
      </div>

      <form className="card" onSubmit={submit}>
        {tab === "peso" && (
          <>
            <h2>Pesaje</h2>
            <div className="field-row">
              <div className="field">
                <label htmlFor="w-date">Fecha</label>
                <input
                  id="w-date"
                  type="date"
                  required
                  max={todayISO()}
                  value={weight.date}
                  onChange={(e) => setWeight({ ...weight, date: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="w-kg">Peso (kg)</label>
                <input
                  id="w-kg"
                  type="number"
                  required
                  step="0.1"
                  min={30}
                  max={300}
                  inputMode="decimal"
                  placeholder="82,4"
                  value={weight.weight_kg}
                  onChange={(e) => setWeight({ ...weight, weight_kg: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="w-fat">% graso (opcional)</label>
              <input
                id="w-fat"
                type="number"
                step="0.1"
                min={3}
                max={70}
                inputMode="decimal"
                value={weight.body_fat_pct}
                onChange={(e) => setWeight({ ...weight, body_fat_pct: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="w-notes">Notas (opcional)</label>
              <input
                id="w-notes"
                value={weight.notes}
                onChange={(e) => setWeight({ ...weight, notes: e.target.value })}
              />
            </div>
          </>
        )}

        {tab === "actividad" && (
          <>
            <h2>Actividad</h2>
            <div className="field">
              <label>Tipo</label>
              <div className="chip-select">
                {ACTIVITY_OPTIONS.map((a) => (
                  <button
                    key={a}
                    type="button"
                    className={activity.activity_type === a ? "on" : ""}
                    onClick={() => setActivity({ ...activity, activity_type: a })}
                  >
                    {ACTIVITY_LABELS[a]}
                  </button>
                ))}
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="a-date">Fecha</label>
                <input
                  id="a-date"
                  type="date"
                  required
                  max={todayISO()}
                  value={activity.date}
                  onChange={(e) => setActivity({ ...activity, date: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="a-dur">Duración (min)</label>
                <input
                  id="a-dur"
                  type="number"
                  required
                  min={1}
                  max={1440}
                  inputMode="numeric"
                  value={activity.duration_min}
                  onChange={(e) => setActivity({ ...activity, duration_min: e.target.value })}
                />
              </div>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="a-dist">Distancia km (opcional)</label>
                <input
                  id="a-dist"
                  type="number"
                  step="0.01"
                  min={0}
                  inputMode="decimal"
                  value={activity.distance_km}
                  onChange={(e) => setActivity({ ...activity, distance_km: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="a-cal">Calorías (opcional)</label>
                <input
                  id="a-cal"
                  type="number"
                  min={0}
                  inputMode="numeric"
                  value={activity.calories}
                  onChange={(e) => setActivity({ ...activity, calories: e.target.value })}
                />
              </div>
            </div>
            {avgSpeed && (
              <p className="hint muted mono">
                {avgSpeed.toFixed(1)} km/h · ritmo {pace} min/km
              </p>
            )}
            <div className="field-row">
              <div className="field">
                <label htmlFor="a-hr">Pulso medio (opcional)</label>
                <input
                  id="a-hr"
                  type="number"
                  min={30}
                  max={250}
                  inputMode="numeric"
                  value={activity.avg_hr}
                  onChange={(e) => setActivity({ ...activity, avg_hr: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="a-hrmax">Pulso máximo (opcional)</label>
                <input
                  id="a-hrmax"
                  type="number"
                  min={30}
                  max={250}
                  inputMode="numeric"
                  value={activity.max_hr}
                  onChange={(e) => setActivity({ ...activity, max_hr: e.target.value })}
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="a-rpe">Esfuerzo percibido 1-10 (opcional)</label>
              <input
                id="a-rpe"
                type="range"
                min={1}
                max={10}
                value={activity.perceived_effort || "5"}
                onChange={(e) => setActivity({ ...activity, perceived_effort: e.target.value })}
              />
              {activity.perceived_effort && (
                <span className="hint mono">{activity.perceived_effort}/10</span>
              )}
            </div>
            <div className="field">
              <label htmlFor="a-notes">Notas (opcional)</label>
              <input
                id="a-notes"
                placeholder="Sensaciones, recorrido…"
                value={activity.notes}
                onChange={(e) => setActivity({ ...activity, notes: e.target.value })}
              />
            </div>
          </>
        )}

        {tab === "comidas" && (
          <>
            <h2>Comidas de hoy</h2>
            {plan ? (
              <>
                {plan.data.nutrition.meals.map((meal) => (
                  <div className="meal-row" key={meal.name}>
                    <div className="row-between">
                      <span className="meal-name">{meal.name}</span>
                      {meal.time && <span className="meal-time">{meal.time}</span>}
                    </div>
                    <div className="segmented">
                      {(
                        [
                          ["full", "Según plan"],
                          ["partial", "A medias"],
                          ["skipped", "Me lo salté"],
                        ] as const
                      ).map(([value, label]) => (
                        <button
                          key={value}
                          type="button"
                          className={mealStatus[meal.name] === value ? "on" : ""}
                          onClick={() => setMealStatus({ ...mealStatus, [meal.name]: value })}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                <div className="field" style={{ marginTop: 12 }}>
                  <label htmlFor="n-water">Agua (litros, opcional)</label>
                  <input
                    id="n-water"
                    type="number"
                    step="0.1"
                    min={0}
                    max={10}
                    inputMode="decimal"
                    value={water}
                    onChange={(e) => setWater(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="n-notes">Notas (opcional)</label>
                  <input
                    id="n-notes"
                    value={nutritionNotes}
                    onChange={(e) => setNutritionNotes(e.target.value)}
                  />
                </div>
              </>
            ) : (
              <p className="muted">
                Las comidas se registran sobre tu plan. Cuando tu plan esté activo podrás marcarlas
                aquí.
              </p>
            )}
          </>
        )}

        {error && <p className="input-error">{error}</p>}
        <button
          className="btn btn-primary"
          disabled={busy || (tab === "comidas" && !plan)}
          style={{ marginTop: 6 }}
        >
          Guardar
        </button>
      </form>
    </div>
  );
}
