import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useRegisterSW } from "virtual:pwa-register/react";

import { api } from "../api";
import { useAuth } from "../auth";
import { clearInstallPrompt, getInstallPrompt, isStandalone, onInstallChange } from "../pwa";
import { useToast } from "../toast";
import { ACTIVITY_LABELS, type IntegrationStatus } from "../types";

const REVISION_ACTIVITIES = ["walk", "run", "swim", "bike", "gym", "hike"];

const ACTIVITY_LEVEL_LABELS: Record<string, string> = {
  sedentary: "Sedentario",
  light: "Ligera",
  moderate: "Moderada",
  active: "Activa",
  very_active: "Muy activa",
};

function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso + "T00:00:00").toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function ProfilePage() {
  const { me, logout, refreshMe } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [editingPlan, setEditingPlan] = useState(false);
  const [activities, setActivities] = useState<string[]>(me?.profile?.preferred_activities ?? []);
  const [days, setDays] = useState(String(me?.profile?.training_days_per_week ?? 3));
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [strava, setStrava] = useState<IntegrationStatus | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [health, setHealth] = useState<IntegrationStatus | null>(null);
  const [syncingHealth, setSyncingHealth] = useState(false);
  const [installPrompt, setInstallPrompt] = useState(getInstallPrompt);
  const [checkingUpdate, setCheckingUpdate] = useState(false);
  const [swRegistration, setSwRegistration] = useState<ServiceWorkerRegistration | null>(null);
  const {
    needRefresh: [needRefresh],
    updateServiceWorker,
  } = useRegisterSW({
    onRegisteredSW: (_url, registration) => setSwRegistration(registration ?? null),
  });

  useEffect(() => onInstallChange(() => setInstallPrompt(getInstallPrompt())), []);

  const loadStrava = () =>
    api<IntegrationStatus>("/api/integrations/strava").then(setStrava).catch(() => {});
  const loadHealth = () =>
    api<IntegrationStatus>("/api/integrations/google-health").then(setHealth).catch(() => {});

  useEffect(() => {
    loadStrava();
    loadHealth();
  }, []);

  // Feedback after coming back from an OAuth screen (Strava or Google Health).
  useEffect(() => {
    const stravaOutcome = params.get("strava");
    const healthOutcome = params.get("salud");
    if (!stravaOutcome && !healthOutcome) return;
    if (stravaOutcome === "conectado") toast("Strava conectado — importando tus actividades");
    else if (stravaOutcome === "denegado") toast("Conexión con Strava cancelada");
    else if (stravaOutcome) toast("No se pudo conectar con Strava");
    if (healthOutcome === "conectado") toast("Google Health conectado — importando tus pesajes");
    else if (healthOutcome === "denegado") toast("Conexión con Google Health cancelada");
    else if (healthOutcome) toast("No se pudo conectar con Google Health");
    setParams({}, { replace: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  if (!me) return null;
  const { user, profile, goal } = me;

  async function syncStrava() {
    setSyncing(true);
    try {
      const r = await api<{ imported: number }>("/api/integrations/strava/sync", {
        method: "POST",
      });
      toast(
        r.imported > 0
          ? `${r.imported} ${r.imported === 1 ? "actividad importada" : "actividades importadas"} de Strava`
          : "Ya estaba todo al día",
      );
      await loadStrava();
    } catch {
      toast("No se pudo sincronizar con Strava");
    } finally {
      setSyncing(false);
    }
  }

  async function disconnectStrava() {
    try {
      await api("/api/integrations/strava", { method: "DELETE" });
      toast("Strava desconectado");
      await loadStrava();
    } catch {
      toast("No se pudo desconectar Strava");
    }
  }

  async function syncHealth() {
    setSyncingHealth(true);
    try {
      const r = await api<{ imported: number }>("/api/integrations/google-health/sync", {
        method: "POST",
      });
      toast(
        r.imported > 0
          ? `${r.imported} ${r.imported === 1 ? "pesaje importado" : "pesajes importados"} de la báscula`
          : "Ya estaba todo al día",
      );
      await loadHealth();
    } catch {
      toast("No se pudo sincronizar con Google Health");
    } finally {
      setSyncingHealth(false);
    }
  }

  async function disconnectHealth() {
    try {
      await api("/api/integrations/google-health", { method: "DELETE" });
      toast("Google Health desconectado");
      await loadHealth();
    } catch {
      toast("No se pudo desconectar Google Health");
    }
  }

  async function installApp() {
    const prompt = installPrompt;
    if (!prompt) return;
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    clearInstallPrompt();
    toast(
      outcome === "accepted"
        ? "Instalando… busca H&F en tu pantalla de inicio"
        : "Instalación cancelada",
    );
  }

  async function checkForUpdate() {
    if (!swRegistration) {
      toast("Actualizaciones no disponibles en este navegador");
      return;
    }
    setCheckingUpdate(true);
    try {
      await swRegistration.update();
      // A found update flips needRefresh via the hook; give it a moment.
      await new Promise((resolve) => setTimeout(resolve, 1500));
      if (!swRegistration.installing && !swRegistration.waiting) {
        toast("Ya tienes la última versión");
      }
    } catch {
      toast("No se pudo comprobar la actualización");
    } finally {
      setCheckingUpdate(false);
    }
  }

  async function requestRevision() {
    setBusy(true);
    try {
      await api("/api/auth/profile", {
        method: "PUT",
        body: { preferred_activities: activities, training_days_per_week: parseInt(days) },
      });
      await api("/api/goal/request-revision", { method: "POST", body: { note } });
      await refreshMe();
      setEditingPlan(false);
      toast("Petición enviada a tu entrenador");
    } catch {
      toast("No se pudo enviar la petición");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="card row-between">
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {user.avatar_url && (
            <img className="avatar" src={user.avatar_url} alt="" referrerPolicy="no-referrer" style={{ width: 48, height: 48 }} />
          )}
          <div>
            <strong>
              {user.first_name} {user.last_name}
            </strong>
            <div className="muted" style={{ fontSize: 14 }}>
              {user.email}
            </div>
          </div>
        </div>
      </div>

      {profile && (
        <div className="card">
          <div className="row-between">
            <div className="eyebrow">Tus datos</div>
            <Link to="/onboarding" className="muted" style={{ fontSize: 14 }}>
              Editar
            </Link>
          </div>
          <div className="tiles" style={{ marginTop: 10 }}>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">Edad · Altura</div>
              <div className="mono">
                {profile.age} años · {profile.height_cm} cm
              </div>
            </div>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">IMC inicial</div>
              <div className="mono">{profile.bmi}</div>
            </div>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">Actividad</div>
              <div>{ACTIVITY_LEVEL_LABELS[profile.activity_level]}</div>
            </div>
            <div className="tile" style={{ border: "none", padding: 0 }}>
              <div className="eyebrow">Te gusta</div>
              <div>
                {profile.preferred_activities.map((a) => ACTIVITY_LABELS[a]).join(", ") || "—"}
              </div>
            </div>
          </div>
        </div>
      )}

      {goal && (
        <div className="card">
          <div className="eyebrow">Objetivo</div>
          <div className="big-number" style={{ fontSize: 40 }}>
            {parseFloat(goal.target_weight_kg)}
            <small>kg</small>
          </div>
          <p className="muted" style={{ margin: "4px 0 0" }}>
            Para el {fmtDate(goal.target_date)} · empezaste en{" "}
            {parseFloat(goal.start_weight_kg)} kg
          </p>
          {goal.admin_message && goal.status === "active" && (
            <>
              <hr className="divider" />
              <div className="eyebrow">Mensaje de tu entrenador</div>
              <p style={{ margin: "4px 0 0" }}>{goal.admin_message}</p>
            </>
          )}
          {goal.status === "active" && (
            <Link className="btn btn-ghost" style={{ marginTop: 12 }} to="/plan">
              Ver plan completo
            </Link>
          )}
        </div>
      )}

      {goal?.status === "active" && (
        <div className="card">
          <div className="eyebrow">Tu plan de ejercicio</div>
          {goal.revision_requested ? (
            <p style={{ margin: "6px 0 0" }}>
              <span className="chip plan">Actualización pedida</span>{" "}
              Tu entrenador está preparando el plan actualizado. Mientras tanto sigue con el
              actual.
            </p>
          ) : editingPlan ? (
            <>
              <p className="muted">
                Marca el ejercicio que estás dispuesto a hacer a partir de ahora y cuéntanos por
                qué. Tu entrenador te preparará un plan actualizado.
              </p>
              <div className="field">
                <label>Ejercicio que quiero hacer</label>
                <div className="chip-select">
                  {REVISION_ACTIVITIES.map((a) => (
                    <button
                      key={a}
                      type="button"
                      className={activities.includes(a) ? "on" : ""}
                      onClick={() =>
                        setActivities((cur) =>
                          cur.includes(a) ? cur.filter((x) => x !== a) : [...cur, a],
                        )
                      }
                    >
                      {ACTIVITY_LABELS[a]}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <label htmlFor="rev-days">Días por semana</label>
                <input
                  id="rev-days"
                  type="number"
                  min={1}
                  max={7}
                  inputMode="numeric"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="rev-note">Cuéntale a tu entrenador (opcional)</label>
                <textarea
                  id="rev-note"
                  rows={2}
                  placeholder="Me he apuntado a la piscina, me duele la rodilla al correr…"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>
              <div className="btn-row">
                <button className="btn btn-ghost" onClick={() => setEditingPlan(false)}>
                  Cancelar
                </button>
                <button
                  className="btn btn-primary"
                  disabled={busy || activities.length === 0}
                  onClick={requestRevision}
                >
                  Pedir plan actualizado
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="muted" style={{ margin: "6px 0 10px" }}>
                ¿Has cambiado de ejercicio o de disponibilidad? Pide a tu entrenador un plan
                actualizado.
              </p>
              <button className="btn btn-secondary" onClick={() => setEditingPlan(true)}>
                Cambiar mi ejercicio y pedir actualización
              </button>
            </>
          )}
        </div>
      )}

      {(strava?.enabled || health?.enabled) && (
        <div className="card">
          <div className="eyebrow">Conexiones</div>
          {strava?.enabled && (strava.connected ? (
            <>
              <p style={{ margin: "6px 0 0" }}>
                <span className="chip strava">Strava</span>{" "}
                Conectado{strava.athlete_name ? ` como ${strava.athlete_name}` : ""}.
              </p>
              <p className="muted" style={{ margin: "6px 0 10px", fontSize: 14 }}>
                Tus salidas (del reloj, Polar Flow o el móvil) se importan solas al abrir la
                app.
                {strava.last_sync_at &&
                  ` Última sincronización: ${new Date(strava.last_sync_at).toLocaleString("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.`}
              </p>
              <div className="btn-row">
                <button className="btn btn-ghost" onClick={disconnectStrava}>
                  Desconectar
                </button>
                <button className="btn btn-secondary" disabled={syncing} onClick={syncStrava}>
                  {syncing ? "Sincronizando…" : "Sincronizar ahora"}
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="muted" style={{ margin: "6px 0 10px" }}>
                Conecta Strava y tus entrenamientos del reloj (vía Polar Flow) se registrarán
                aquí automáticamente.
              </p>
              {strava.auth_url && (
                <a className="btn btn-strava" href={strava.auth_url}>
                  Conectar con Strava
                </a>
              )}
            </>
          ))}

          {strava?.enabled && health?.enabled && <hr className="divider" />}

          {health?.enabled &&
            (health.connected ? (
              <>
                <p style={{ margin: "6px 0 0" }}>
                  <span className="chip health">Google Health</span> Conectado.
                </p>
                <p className="muted" style={{ margin: "6px 0 10px", fontSize: 14 }}>
                  Los pesajes de tu báscula se importan solos al abrir la app.
                  {health.last_sync_at &&
                    ` Última sincronización: ${new Date(health.last_sync_at).toLocaleString("es-ES", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}.`}
                </p>
                <div className="btn-row">
                  <button className="btn btn-ghost" onClick={disconnectHealth}>
                    Desconectar
                  </button>
                  <button
                    className="btn btn-secondary"
                    disabled={syncingHealth}
                    onClick={syncHealth}
                  >
                    {syncingHealth ? "Sincronizando…" : "Sincronizar ahora"}
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="muted" style={{ margin: "6px 0 10px" }}>
                  Conecta Google Health y los pesajes de tu báscula entrarán solos en tu
                  curva de peso.
                </p>
                {health.auth_url && (
                  <a className="btn btn-health" href={health.auth_url}>
                    Conectar con Google Health
                  </a>
                )}
              </>
            ))}
        </div>
      )}

      <div className="card">
        <div className="eyebrow">Aplicación</div>
        {needRefresh ? (
          <>
            <p style={{ margin: "6px 0 10px" }}>
              Hay una versión nueva lista para usar.
            </p>
            <button className="btn btn-primary" onClick={() => updateServiceWorker(true)}>
              Actualizar ahora
            </button>
          </>
        ) : isStandalone() ? (
          <>
            <p className="muted" style={{ margin: "6px 0 10px", fontSize: 14 }}>
              Estás usando la app instalada · versión del{" "}
              <span className="mono">{__BUILD_DATE__}</span>.
            </p>
            <button className="btn btn-secondary" disabled={checkingUpdate} onClick={checkForUpdate}>
              {checkingUpdate ? "Comprobando…" : "Buscar actualización"}
            </button>
          </>
        ) : installPrompt ? (
          <>
            <p className="muted" style={{ margin: "6px 0 10px" }}>
              Instala H&amp;F en tu móvil: se abre a pantalla completa, con su icono, como
              cualquier app.
            </p>
            <button className="btn btn-primary" onClick={installApp}>
              Instalar en este dispositivo
            </button>
          </>
        ) : (
          <p className="muted" style={{ margin: "6px 0 0", fontSize: 14 }}>
            Para instalarla: abre el menú ⋮ de Chrome y toca «Añadir a pantalla de inicio»
            (o «Instalar app»). Versión del <span className="mono">{__BUILD_DATE__}</span>.
          </p>
        )}
      </div>

      <button
        className="btn btn-ghost"
        onClick={() => {
          logout();
          navigate("/login");
        }}
      >
        Cerrar sesión
      </button>
    </div>
  );
}
