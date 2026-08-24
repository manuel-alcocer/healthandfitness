import { useMemo, useState, type FormEvent } from "react";

import { api, ApiError } from "../../api";
import { useToast } from "../../toast";
import { ACTIVITY_LABELS } from "../../types";

const ACTIVITY_OPTIONS = ["walk", "run", "swim", "bike", "gym", "hike", "other"];

/** Log one exercise session on a given day, with its measured metrics. */
export default function ActivityForm({
  date,
  defaultType,
  planDay,
  onSaved,
}: {
  date: string;
  defaultType?: string;
  planDay?: number | null;
  onSaved?: () => void;
}) {
  const [form, setForm] = useState({
    activity_type: defaultType || "walk",
    duration_min: "",
    distance_km: "",
    avg_hr: "",
    max_hr: "",
    calories: "",
    perceived_effort: "",
    notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const set = (key: string, value: string) => setForm((f) => ({ ...f, [key]: value }));

  const avgSpeed = useMemo(() => {
    const dist = parseFloat(form.distance_km);
    const dur = parseFloat(form.duration_min);
    if (!dist || !dur) return null;
    return dist / (dur / 60);
  }, [form.distance_km, form.duration_min]);

  const pace = useMemo(() => {
    const dist = parseFloat(form.distance_km);
    const dur = parseFloat(form.duration_min);
    if (!dist || !dur) return null;
    const minPerKm = dur / dist;
    const min = Math.floor(minPerKm);
    const sec = Math.round((minPerKm - min) * 60);
    return `${min}:${sec.toString().padStart(2, "0")}`;
  }, [form.distance_km, form.duration_min]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/tracking/activities", {
        method: "POST",
        body: {
          date,
          activity_type: form.activity_type,
          duration_min: parseInt(form.duration_min),
          distance_km: form.distance_km || null,
          avg_hr: form.avg_hr ? parseInt(form.avg_hr) : null,
          max_hr: form.max_hr ? parseInt(form.max_hr) : null,
          avg_speed_kmh: avgSpeed ? avgSpeed.toFixed(2) : null,
          calories: form.calories ? parseInt(form.calories) : null,
          perceived_effort: form.perceived_effort ? parseInt(form.perceived_effort) : null,
          plan_day: planDay ?? null,
          notes: form.notes,
        },
      });
      toast("Actividad registrada");
      setForm({ ...form, duration_min: "", distance_km: "", avg_hr: "", max_hr: "",
                calories: "", perceived_effort: "", notes: "" });
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar. Revisa los campos.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="field">
        <label>Tipo</label>
        <div className="chip-select">
          {ACTIVITY_OPTIONS.map((a) => (
            <button
              key={a}
              type="button"
              className={form.activity_type === a ? "on" : ""}
              onClick={() => set("activity_type", a)}
            >
              {ACTIVITY_LABELS[a]}
            </button>
          ))}
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="a-dur">Duración (min)</label>
          <input
            id="a-dur"
            type="number"
            required
            min={1}
            max={1440}
            inputMode="numeric"
            value={form.duration_min}
            onChange={(e) => set("duration_min", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="a-dist">Distancia km (opcional)</label>
          <input
            id="a-dist"
            type="number"
            step="0.01"
            min={0}
            inputMode="decimal"
            value={form.distance_km}
            onChange={(e) => set("distance_km", e.target.value)}
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
            value={form.avg_hr}
            onChange={(e) => set("avg_hr", e.target.value)}
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
            value={form.max_hr}
            onChange={(e) => set("max_hr", e.target.value)}
          />
        </div>
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="a-cal">Calorías (opcional)</label>
          <input
            id="a-cal"
            type="number"
            min={0}
            inputMode="numeric"
            value={form.calories}
            onChange={(e) => set("calories", e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="a-rpe">Esfuerzo 1-10 (opcional)</label>
          <input
            id="a-rpe"
            type="number"
            min={1}
            max={10}
            inputMode="numeric"
            value={form.perceived_effort}
            onChange={(e) => set("perceived_effort", e.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="a-notes">Notas (opcional)</label>
        <input
          id="a-notes"
          placeholder="Sensaciones, recorrido…"
          value={form.notes}
          onChange={(e) => set("notes", e.target.value)}
        />
      </div>
      {error && <p className="input-error">{error}</p>}
      <button className="btn btn-primary" disabled={busy}>
        Guardar actividad
      </button>
    </form>
  );
}
