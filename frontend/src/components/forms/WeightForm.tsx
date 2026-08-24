import { useEffect, useState, type FormEvent } from "react";

import { api, ApiError } from "../../api";
import { useToast } from "../../toast";
import type { WeightEntry } from "../../types";

/** Biometric log for one day: weight (plus optional body fat and notes). */
export default function WeightForm({ date, onSaved }: { date: string; onSaved?: () => void }) {
  const [weightKg, setWeightKg] = useState("");
  const [bodyFat, setBodyFat] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  useEffect(() => {
    api<{ results: WeightEntry[] }>("/api/tracking/weights?limit=200")
      .then((r) => {
        const existing = r.results.find((e) => e.date === date);
        setWeightKg(existing ? String(parseFloat(existing.weight_kg)) : "");
        setBodyFat(existing?.body_fat_pct ?? "");
        setNotes(existing?.notes ?? "");
      })
      .catch(() => {});
  }, [date]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/tracking/weights", {
        method: "POST",
        body: { date, weight_kg: weightKg, body_fat_pct: bodyFat || null, notes },
      });
      toast("Peso guardado");
      onSaved?.();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="field-row">
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
            value={weightKg}
            onChange={(e) => setWeightKg(e.target.value)}
          />
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
            value={bodyFat}
            onChange={(e) => setBodyFat(e.target.value)}
          />
        </div>
      </div>
      <div className="field">
        <label htmlFor="w-notes">Notas (opcional)</label>
        <input id="w-notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      {error && <p className="input-error">{error}</p>}
      <button className="btn btn-primary" disabled={busy}>
        Guardar peso
      </button>
    </form>
  );
}
