import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { api } from "../api";
import { useAuth } from "../auth";

function fmtDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso + "T00:00:00").toLocaleDateString("es-ES", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

export default function Waiting() {
  const { me, refreshMe } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const goal = me?.goal;

  if (!goal || goal.status === "active") return <Navigate to="/" replace />;

  if (goal.status === "pending") {
    return (
      <div className="card waiting">
        <div className="pulse" aria-hidden>
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M4 12h3l2.5-6 4 12 2.5-6h4" />
          </svg>
        </div>
        <h2>Tu plan está en preparación</h2>
        <p className="muted">
          Tu entrenador está revisando tu objetivo de{" "}
          <strong className="mono">{parseFloat(goal.target_weight_kg)} kg</strong> para el{" "}
          <strong>{fmtDate(goal.target_date)}</strong>. Te prepararemos un plan de alimentación y
          ejercicio a tu medida. Vuelve pronto.
        </p>
        <button className="btn btn-secondary" onClick={() => refreshMe()}>
          Comprobar de nuevo
        </button>
      </div>
    );
  }

  // status === "suggested": the goal was judged unrealistic.
  return (
    <div className="stack">
      <div className="card">
        <div className="eyebrow">Revisión de tu entrenador</div>
        <h2>Tu objetivo necesita un ajuste</h2>
        <p>{goal.admin_message}</p>
        <hr className="divider" />
        <div className="row-between">
          <div>
            <div className="eyebrow">Pediste</div>
            <div className="mono">
              {parseFloat(goal.target_weight_kg)} kg · {fmtDate(goal.target_date)}
            </div>
          </div>
          <div>
            <div className="eyebrow">Te proponemos</div>
            <div className="mono" style={{ color: "var(--brand-ink)", fontWeight: 600 }}>
              {goal.suggested_target_weight_kg
                ? `${parseFloat(goal.suggested_target_weight_kg)} kg · ${fmtDate(goal.suggested_target_date)}`
                : "—"}
            </div>
          </div>
        </div>
        <hr className="divider" />
        <div className="stack">
          <button
            className="btn btn-primary"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              try {
                await api("/api/goal/accept-suggestion", { method: "POST" });
                await refreshMe();
                navigate("/");
              } finally {
                setBusy(false);
              }
            }}
          >
            Aceptar el plan propuesto
          </button>
          <button
            className="btn btn-ghost"
            onClick={() => navigate("/onboarding?paso=objetivo")}
          >
            Cambiar mi objetivo
          </button>
        </div>
      </div>
    </div>
  );
}
