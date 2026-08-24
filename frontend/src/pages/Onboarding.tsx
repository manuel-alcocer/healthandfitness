import { useMemo, useState, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { api, ApiError } from "../api";
import { useAuth } from "../auth";
import { ACTIVITY_LABELS } from "../types";

const ACTIVITY_OPTIONS = ["walk", "run", "swim", "bike", "gym", "hike"];

export default function Onboarding() {
  const { me, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // "?paso=objetivo" jumps straight to the goal step (used to resubmit a goal).
  const [step, setStep] = useState(params.get("paso") === "objetivo" && me?.profile ? 2 : 1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const p = me?.profile;
  const [form, setForm] = useState({
    sex: p?.sex ?? "",
    birth_date: p?.birth_date ?? "",
    height_cm: p?.height_cm?.toString() ?? "",
    initial_weight_kg: p?.initial_weight_kg ?? "",
    activity_level: p?.activity_level ?? "light",
    resting_hr: p?.resting_hr?.toString() ?? "",
    body_fat_pct: p?.body_fat_pct ?? "",
    waist_cm: p?.waist_cm?.toString() ?? "",
    health_conditions: p?.health_conditions ?? "",
    dietary_preferences: p?.dietary_preferences ?? "",
    training_days_per_week: p?.training_days_per_week?.toString() ?? "3",
    preferred_activities: p?.preferred_activities ?? ([] as string[]),
    equipment: p?.equipment ?? "",
  });
  const [goal, setGoal] = useState({
    target_weight_kg: "",
    target_date: "",
    motivation: "",
  });

  const set = (key: string, value: unknown) => setForm((f) => ({ ...f, [key]: value }));

  const weeklyRate = useMemo(() => {
    const w = parseFloat(form.initial_weight_kg);
    const t = parseFloat(goal.target_weight_kg);
    if (!w || !t || !goal.target_date) return null;
    const weeks = (new Date(goal.target_date).getTime() - Date.now()) / (7 * 86400e3);
    if (weeks <= 0) return null;
    return (w - t) / weeks;
  }, [form.initial_weight_kg, goal]);

  async function submitProfile(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/auth/profile", {
        method: "PUT",
        body: {
          ...form,
          height_cm: parseInt(form.height_cm),
          training_days_per_week: parseInt(form.training_days_per_week),
          resting_hr: form.resting_hr ? parseInt(form.resting_hr) : null,
          body_fat_pct: form.body_fat_pct || null,
          waist_cm: form.waist_cm ? parseInt(form.waist_cm) : null,
        },
      });
      await refreshMe();
      setStep(2);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudieron guardar los datos.");
    } finally {
      setBusy(false);
    }
  }

  async function submitGoal(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/goal", { method: "POST", body: goal });
      await refreshMe();
      navigate("/espera");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el objetivo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-solo stack">
      <div className="steps" aria-hidden>
        <span className="on" />
        <span className={step === 2 ? "on" : ""} />
      </div>

      {step === 1 ? (
        <form className="card" onSubmit={submitProfile}>
          <div className="eyebrow">Paso 1 de 2</div>
          <h2>Cuéntanos sobre ti</h2>
          <p className="muted">Con estos datos tu entrenador ajustará el plan a tu cuerpo.</p>

          <div className="field">
            <label>Sexo</label>
            <div className="segmented" role="radiogroup" aria-label="Sexo">
              {(["M", "F"] as const).map((s) => (
                <button
                  key={s}
                  type="button"
                  className={form.sex === s ? "on" : ""}
                  onClick={() => set("sex", s)}
                >
                  {s === "M" ? "Hombre" : "Mujer"}
                </button>
              ))}
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="birth">Fecha de nacimiento</label>
              <input
                id="birth"
                type="date"
                required
                value={form.birth_date}
                onChange={(e) => set("birth_date", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="height">Altura (cm)</label>
              <input
                id="height"
                type="number"
                required
                min={120}
                max={230}
                inputMode="numeric"
                value={form.height_cm}
                onChange={(e) => set("height_cm", e.target.value)}
              />
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="weight">Peso actual (kg)</label>
              <input
                id="weight"
                type="number"
                required
                step="0.1"
                min={30}
                max={300}
                inputMode="decimal"
                value={form.initial_weight_kg}
                onChange={(e) => set("initial_weight_kg", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="fat">% graso (opcional)</label>
              <input
                id="fat"
                type="number"
                step="0.1"
                min={3}
                max={70}
                inputMode="decimal"
                value={form.body_fat_pct}
                onChange={(e) => set("body_fat_pct", e.target.value)}
              />
            </div>
          </div>

          <div className="field">
            <label htmlFor="activity">Actividad actual</label>
            <select
              id="activity"
              value={form.activity_level}
              onChange={(e) => set("activity_level", e.target.value)}
            >
              <option value="sedentary">Sedentario</option>
              <option value="light">Ligera (1-2 días/semana)</option>
              <option value="moderate">Moderada (3-4 días/semana)</option>
              <option value="active">Activa (5-6 días/semana)</option>
              <option value="very_active">Muy activa (a diario)</option>
            </select>
          </div>

          <div className="field-row">
            <div className="field">
              <label htmlFor="rhr">Pulso en reposo (opcional)</label>
              <input
                id="rhr"
                type="number"
                min={30}
                max={120}
                inputMode="numeric"
                value={form.resting_hr}
                onChange={(e) => set("resting_hr", e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="waist">Cintura cm (opcional)</label>
              <input
                id="waist"
                type="number"
                min={40}
                max={200}
                inputMode="numeric"
                value={form.waist_cm}
                onChange={(e) => set("waist_cm", e.target.value)}
              />
            </div>
          </div>

          <div className="field">
            <label>¿Qué ejercicio te gusta?</label>
            <div className="chip-select">
              {ACTIVITY_OPTIONS.map((a) => (
                <button
                  key={a}
                  type="button"
                  className={form.preferred_activities.includes(a) ? "on" : ""}
                  onClick={() =>
                    set(
                      "preferred_activities",
                      form.preferred_activities.includes(a)
                        ? form.preferred_activities.filter((x) => x !== a)
                        : [...form.preferred_activities, a],
                    )
                  }
                >
                  {ACTIVITY_LABELS[a]}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label htmlFor="days">Días que puedes entrenar por semana</label>
            <input
              id="days"
              type="number"
              min={1}
              max={7}
              required
              inputMode="numeric"
              value={form.training_days_per_week}
              onChange={(e) => set("training_days_per_week", e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="equipment">Material o instalaciones (opcional)</label>
            <input
              id="equipment"
              placeholder="Gimnasio, piscina, bici…"
              value={form.equipment}
              onChange={(e) => set("equipment", e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="health">Salud a tener en cuenta (opcional)</label>
            <textarea
              id="health"
              rows={2}
              placeholder="Lesiones, medicación, condiciones…"
              value={form.health_conditions}
              onChange={(e) => set("health_conditions", e.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="diet">Alimentación: alergias o preferencias (opcional)</label>
            <textarea
              id="diet"
              rows={2}
              placeholder="Sin lactosa, vegetariano, no me gusta el pescado…"
              value={form.dietary_preferences}
              onChange={(e) => set("dietary_preferences", e.target.value)}
            />
          </div>

          {error && <p className="input-error">{error}</p>}
          <button className="btn btn-primary" disabled={busy || !form.sex}>
            Continuar
          </button>
        </form>
      ) : (
        <form className="card" onSubmit={submitGoal}>
          <div className="eyebrow">Paso 2 de 2</div>
          <h2>Tu objetivo</h2>
          <p className="muted">
            Tu entrenador lo revisará y te preparará un plan de alimentación y ejercicio a medida.
          </p>

          <div className="field-row">
            <div className="field">
              <label htmlFor="target-w">Peso objetivo (kg)</label>
              <input
                id="target-w"
                type="number"
                required
                step="0.1"
                min={30}
                max={300}
                inputMode="decimal"
                value={goal.target_weight_kg}
                onChange={(e) => setGoal({ ...goal, target_weight_kg: e.target.value })}
              />
            </div>
            <div className="field">
              <label htmlFor="target-d">Para la fecha</label>
              <input
                id="target-d"
                type="date"
                required
                value={goal.target_date}
                onChange={(e) => setGoal({ ...goal, target_date: e.target.value })}
              />
            </div>
          </div>

          {weeklyRate !== null && (
            <p className="hint muted">
              Eso supone un ritmo de{" "}
              <strong className="mono">
                {Math.abs(weeklyRate).toFixed(2)} kg/semana{" "}
                {weeklyRate >= 0 ? "de pérdida" : "de ganancia"}
              </strong>
              . Un ritmo saludable de pérdida suele estar entre 0,3 y 1 kg por semana.
            </p>
          )}

          <div className="field">
            <label htmlFor="motivation">¿Por qué quieres conseguirlo? (opcional)</label>
            <textarea
              id="motivation"
              rows={3}
              placeholder="Tu motivación ayuda a diseñar un plan que puedas mantener."
              value={goal.motivation}
              onChange={(e) => setGoal({ ...goal, motivation: e.target.value })}
            />
          </div>

          {error && <p className="input-error">{error}</p>}
          <div className="btn-row">
            <button type="button" className="btn btn-ghost" onClick={() => setStep(1)}>
              Atrás
            </button>
            <button className="btn btn-primary" disabled={busy}>
              Enviar a mi entrenador
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
