import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";

import { api } from "../api";
import ActivityForm from "../components/forms/ActivityForm";
import MealsForm from "../components/forms/MealsForm";
import WeightForm from "../components/forms/WeightForm";
import { useToast } from "../toast";
import {
  ACTIVITY_LABELS,
  mealsForDate,
  planDayOf,
  type ActivityEntry,
  type CalendarDay,
  type CalendarMonth,
  type NutritionEntry,
  type Plan,
  type PlanSession,
  type WeightEntry,
} from "../types";

function todayISO() {
  const d = new Date();
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

function shiftDate(iso: string, days: number) {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + days);
  const off = d.getTimezoneOffset();
  return new Date(d.getTime() - off * 60000).toISOString().slice(0, 10);
}

const LEVEL_CHIP: Record<string, { text: string; cls: string } | undefined> = {
  red: { text: "Nada o poco", cls: "bad" },
  yellow: { text: "A medias", cls: "warn" },
  green: { text: "Casi todo", cls: "good" },
  medal: { text: "🏅 Completo", cls: "good" },
};

const MEAL_STATUS_CHIP: Record<string, { text: string; cls: string }> = {
  full: { text: "Según plan", cls: "good" },
  partial: { text: "A medias", cls: "warn" },
  skipped: { text: "Saltada", cls: "bad" },
};

function fmtTarget(session: PlanSession): string {
  const t = session.target ?? {};
  const parts: string[] = [];
  if (t.distance_km) parts.push(`${t.distance_km} km`);
  if (t.duration_min) parts.push(`${t.duration_min} min`);
  if (t.hr_zone) parts.push(`zona ${t.hr_zone}`);
  if (t.pace_min_km) parts.push(`${t.pace_min_km} min/km`);
  return parts.join(" · ");
}

export default function DayPage() {
  const { fecha } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const toast = useToast();
  const date = fecha && /^\d{4}-\d{2}-\d{2}$/.test(fecha) ? fecha : todayISO();
  const today = todayISO();
  const isPastOrToday = date <= today;

  const [plan, setPlan] = useState<Plan | null>(null);
  const [dayInfo, setDayInfo] = useState<CalendarDay | null>(null);
  const [nutrition, setNutrition] = useState<NutritionEntry | null>(null);
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [weight, setWeight] = useState<WeightEntry | null>(null);
  const [openMeal, setOpenMeal] = useState<string | null>(null);
  const [activityOpen, setActivityOpen] = useState(false);
  const [openForm, setOpenForm] = useState<"comidas" | "actividad" | "biometria" | null>(
    params.get("registro") ? "comidas" : null,
  );
  const [reload, setReload] = useState(0);

  useEffect(() => {
    api<Plan>("/api/plan").then(setPlan).catch(() => {});
  }, []);

  // Route params change without remounting, so collapse day-specific state.
  useEffect(() => {
    setOpenMeal(null);
    setActivityOpen(false);
    setOpenForm(params.get("registro") ? "comidas" : null);
  }, [date, params]);

  useEffect(() => {
    api<CalendarMonth>(`/api/calendar?month=${date.slice(0, 7)}`)
      .then((m) => setDayInfo(m.days.find((d) => d.date === date) ?? null))
      .catch(() => {});
    api<{ results: NutritionEntry[] }>("/api/tracking/nutrition?limit=200")
      .then((r) => setNutrition(r.results.find((e) => e.date === date) ?? null))
      .catch(() => {});
    api<{ results: ActivityEntry[] }>("/api/tracking/activities?limit=200")
      .then((r) => setActivities(r.results.filter((e) => e.date === date)))
      .catch(() => {});
    api<{ results: WeightEntry[] }>("/api/tracking/weights?limit=200")
      .then((r) => setWeight(r.results.find((e) => e.date === date) ?? null))
      .catch(() => {});
  }, [date, reload]);

  const refresh = useCallback(() => setReload((n) => n + 1), []);

  async function removeActivity(id: number) {
    await api(`/api/tracking/activities/${id}`, { method: "DELETE" });
    toast("Actividad eliminada");
    refresh();
  }

  function activityRow(a: ActivityEntry) {
    return (
      <div className="entry-row" key={a.id}>
        <span className="what">
          <strong>{a.title || ACTIVITY_LABELS[a.activity_type]}</strong>
          {a.source === "strava" && (
            <span className="chip strava" style={{ fontSize: 11, marginLeft: 6 }}>
              Strava
            </span>
          )}
          <span className="muted mono" style={{ fontSize: 13 }}>
            {" "}· {a.duration_min} min
            {a.distance_km && ` · ${parseFloat(a.distance_km)} km`}
            {a.avg_hr && ` · ${a.avg_hr} ppm`}
            {a.avg_speed_kmh && ` · ${parseFloat(a.avg_speed_kmh)} km/h`}
          </span>
        </span>
        <button className="del" aria-label="Eliminar" onClick={() => removeActivity(a.id)}>
          ✕
        </button>
      </div>
    );
  }

  const weekday = planDayOf(date);
  const meals = plan ? mealsForDate(plan.data, date) : [];
  const session =
    plan?.data.exercise.weekly_schedule.find((s) => s.day === weekday) ?? null;
  const loggedByName = new Map(nutrition?.meals.map((m) => [m.name, m]) ?? []);
  const levelChip = dayInfo ? LEVEL_CHIP[dayInfo.level] : undefined;
  const label = new Date(date + "T00:00:00").toLocaleDateString("es-ES", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  return (
    <div className="stack">
      {/* Day header with prev/next navigation */}
      <div className="row-between">
        <button className="cal-nav" aria-label="Día anterior" onClick={() => navigate(`/dia/${shiftDate(date, -1)}`)}>
          ‹
        </button>
        <div style={{ textAlign: "center" }}>
          <strong style={{ textTransform: "capitalize" }}>{label}</strong>
          {date === today && <div className="eyebrow">Hoy</div>}
        </div>
        <button className="cal-nav" aria-label="Día siguiente" onClick={() => navigate(`/dia/${shiftDate(date, 1)}`)}>
          ›
        </button>
      </div>

      {/* ------ Comidas ------ */}
      <div className="card">
        <div className="row-between">
          <h2 className="section-title" style={{ margin: 0 }}>Comidas</h2>
          {levelChip && <span className={`chip ${levelChip.cls}`}>{levelChip.text}</span>}
        </div>
        {meals.length ? (
          meals.map((meal) => {
            const log = loggedByName.get(meal.name);
            const chip = log ? MEAL_STATUS_CHIP[log.status] : null;
            const open = openMeal === meal.name;
            return (
              <div className="meal-row" key={meal.name}>
                <button
                  className="expand-head"
                  aria-expanded={open}
                  onClick={() => setOpenMeal(open ? null : meal.name)}
                >
                  <span>
                    <span className="meal-name">{meal.name}</span>
                    {meal.time && <span className="meal-time"> · {meal.time}</span>}
                    <br />
                    <span className="muted" style={{ fontSize: 14 }}>
                      {log?.option ?? `${meal.options.length} opciones`}
                    </span>
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    {chip ? (
                      <span className={`chip ${chip.cls}`} style={{ fontSize: 12 }}>{chip.text}</span>
                    ) : (
                      <span className="muted" style={{ fontSize: 12 }}>Sin registrar</span>
                    )}
                    <span aria-hidden>{open ? "▾" : "▸"}</span>
                  </span>
                </button>
                {open && (
                  <ul style={{ margin: "6px 0 0", paddingLeft: 18, color: "var(--ink-2)" }}>
                    {meal.options.map((option, i) => (
                      <li key={i} style={log?.option === option ? { color: "var(--brand-ink)", fontWeight: 600 } : undefined}>
                        {option}
                        {log?.option === option && " ✓"}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })
        ) : (
          <p className="muted" style={{ margin: 0 }}>El menú aparecerá cuando tu plan esté activo.</p>
        )}
      </div>

      {/* ------ Actividad ------ */}
      <div className="card">
        <h2 className="section-title" style={{ margin: 0 }}>Actividad</h2>
        {session ? (
          session.type === "rest" ? (
            <>
              <p style={{ marginBottom: 0 }}>
                Descanso. También es parte del plan.
                {activities.length > 0 && " ¡Y aun así entrenaste!"}
              </p>
              {activities.map(activityRow)}
            </>
          ) : (
            <div className="meal-row" style={{ borderBottom: "none" }}>
              <button
                className="expand-head"
                aria-expanded={activityOpen}
                onClick={() => setActivityOpen(!activityOpen)}
              >
                <span>
                  <span className="meal-name">{session.title || ACTIVITY_LABELS[session.type]}</span>{" "}
                  <span className="chip plan" style={{ fontSize: 12 }}>{ACTIVITY_LABELS[session.type]}</span>
                  <br />
                  <span className="mono muted" style={{ fontSize: 13 }}>{fmtTarget(session)}</span>
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  {isPastOrToday &&
                    (activities.length ? (
                      <span className="chip good" style={{ fontSize: 12 }}>
                        {dayInfo?.exercise_ratio != null
                          ? `${Math.round(dayInfo.exercise_ratio * 100)}%`
                          : "Hecha"}
                      </span>
                    ) : (
                      <span className="muted" style={{ fontSize: 12 }}>Sin registrar</span>
                    ))}
                  <span aria-hidden>{activityOpen ? "▾" : "▸"}</span>
                </span>
              </button>
              {activityOpen && (
                <div>
                  {session.details && <p className="muted" style={{ margin: "6px 0" }}>{session.details}</p>}
                  {activities.map(activityRow)}
                </div>
              )}
            </div>
          )
        ) : (
          <>
            <p className="muted" style={{ margin: 0 }}>La sesión aparecerá cuando tu plan esté activo.</p>
            {activities.map(activityRow)}
          </>
        )}
      </div>

      {/* ------ Registro ------ */}
      {isPastOrToday && (
        <div className="card">
          <h2 className="section-title" style={{ margin: "0 0 4px" }}>Registro</h2>
          <p className="muted" style={{ margin: "0 0 8px", fontSize: 14 }}>
            Apunta lo que hiciste este día. Los datos biométricos son opcionales.
          </p>
          {(
            [
              ["comidas", "Comidas realizadas", nutrition ? "✓" : null],
              ["actividad", "Actividad realizada", activities.length ? "✓" : null],
              ["biometria", `Datos biométricos${weight ? ` · ${parseFloat(weight.weight_kg)} kg` : " (opcional)"}`, weight ? "✓" : null],
            ] as const
          ).map(([key, title, done]) => (
            <div key={key} className="reg-section">
              <button
                className="expand-head"
                aria-expanded={openForm === key}
                onClick={() => setOpenForm(openForm === key ? null : key)}
              >
                <span style={{ fontWeight: 600 }}>
                  {title} {done && <span style={{ color: "var(--brand)" }}>{done}</span>}
                </span>
                <span aria-hidden>{openForm === key ? "▾" : "▸"}</span>
              </button>
              {openForm === key && (
                <div style={{ paddingTop: 8 }}>
                  {key === "comidas" &&
                    (plan ? (
                      <MealsForm date={date} plan={plan.data} onSaved={refresh} />
                    ) : (
                      <p className="muted">Necesitas un plan activo para registrar comidas.</p>
                    ))}
                  {key === "actividad" && (
                    <ActivityForm
                      date={date}
                      defaultType={session && session.type !== "rest" ? session.type : undefined}
                      planDay={session && session.type !== "rest" ? weekday : null}
                      onSaved={refresh}
                    />
                  )}
                  {key === "biometria" && <WeightForm date={date} onSaved={refresh} />}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
