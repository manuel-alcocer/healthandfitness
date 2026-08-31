import { useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "../../api";
import { useToast } from "../../toast";
import type { MealLog, NutritionEntry, PlanMeal } from "../../types";

/** Log the day's meals against that date's own menu (status + chosen option). */
export default function MealsForm({
  date,
  meals,
  onSaved,
}: {
  date: string;
  meals: PlanMeal[];
  onSaved?: () => void;
}) {
  const [mealLog, setMealLog] = useState<Record<string, MealLog>>({});
  const [water, setWater] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    api<{ results: NutritionEntry[] }>("/api/tracking/nutrition?limit=200")
      .then((r) => {
        const existing = r.results.find((e) => e.date === date);
        const map: Record<string, MealLog> = {};
        existing?.meals.forEach((m) => (map[m.name] = m));
        setMealLog(map);
        setWater(existing?.water_l ?? "");
        setNotes(existing?.notes ?? "");
      })
      .catch(() => {});
  }, [date]);

  const setMeal = (name: string, patch: Partial<MealLog>) =>
    setMealLog((cur) => {
      const base: MealLog = cur[name] ?? { name, status: "skipped" };
      return { ...cur, [name]: { ...base, ...patch } };
    });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payloadMeals = meals.map((m) => {
        const log = mealLog[m.name];
        return {
          name: m.name,
          status: log?.status ?? "skipped",
          ...(log?.option ? { option: log.option } : {}),
        };
      });
      await api("/api/tracking/nutrition", {
        method: "POST",
        body: { date, meals: payloadMeals, water_l: water || null, notes },
      });
      toast("Comidas guardadas");
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      {meals.map((meal) => {
        const log = mealLog[meal.name];
        const eaten = log?.status === "full" || log?.status === "partial";
        return (
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
                  className={log?.status === value ? "on" : ""}
                  onClick={() => setMeal(meal.name, { status: value })}
                >
                  {label}
                </button>
              ))}
            </div>
            {eaten && meal.options.length > 1 && (
              <div className="chip-select">
                {meal.options.map((option) => (
                  <button
                    key={option}
                    type="button"
                    className={log?.option === option ? "on" : ""}
                    onClick={() =>
                      setMeal(meal.name, {
                        option: log?.option === option ? undefined : option,
                      })
                    }
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}
          </div>
        );
      })}
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
        <input id="n-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      {error && <p className="input-error">{error}</p>}
      <button className="btn btn-primary" disabled={busy}>
        Guardar comidas
      </button>
    </form>
  );
}
