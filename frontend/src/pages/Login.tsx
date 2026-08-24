import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { useState } from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../auth";

export default function Login() {
  const { me, googleClientId, loginWithCredential } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (me) return <Navigate to="/" replace />;

  return (
    <div className="login-hero">
      <div>
        <div className="eyebrow">Tu entrenador personal</div>
        <h1 className="login-mark">
          Health<em>&amp;Fitness</em>
        </h1>
      </div>
      <p className="tagline">
        Marca tu objetivo de peso, recibe un plan de alimentación y ejercicio hecho para ti, y
        registra cada día para saber si vas por buen camino.
      </p>
      {busy ? (
        <p className="muted">Entrando…</p>
      ) : googleClientId ? (
        <GoogleOAuthProvider clientId={googleClientId}>
          <GoogleLogin
            onSuccess={async (resp) => {
              if (!resp.credential) return;
              setBusy(true);
              setError(null);
              try {
                await loginWithCredential(resp.credential);
              } catch {
                setError("No se pudo iniciar sesión. Inténtalo de nuevo.");
                setBusy(false);
              }
            }}
            onError={() => setError("Google no ha podido identificarte. Inténtalo de nuevo.")}
            text="continue_with"
            locale="es"
            width="280"
          />
        </GoogleOAuthProvider>
      ) : (
        <p className="login-note">
          El inicio de sesión con Google aún no está configurado en este servidor.
        </p>
      )}
      {error && <p className="input-error">{error}</p>}
      <p className="login-note">
        Entras con tu cuenta de Google. Tras completar tus datos, tu entrenador revisará tu
        objetivo y preparará tu plan personalizado.
      </p>
    </div>
  );
}
