import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { api, clearTokens, getAccessToken, storeTokens } from "./api";
import type { Me, User } from "./types";

interface AuthState {
  me: Me | null;
  loading: boolean;
  googleClientId: string | null;
  loginWithCredential: (credential: string) => Promise<void>;
  refreshMe: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [googleClientId, setGoogleClientId] = useState<string | null>(null);

  const refreshMe = useCallback(async () => {
    const data = await api<Me>("/api/auth/me");
    setMe(data);
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const config = await api<{ google_client_id: string }>("/api/auth/config");
        setGoogleClientId(config.google_client_id || null);
      } catch {
        setGoogleClientId(null);
      }
      if (getAccessToken()) {
        try {
          await refreshMe();
        } catch {
          clearTokens();
        }
      }
      setLoading(false);
    })();
  }, [refreshMe]);

  const loginWithCredential = useCallback(
    async (credential: string) => {
      const data = await api<{ access: string; refresh: string; user: User }>(
        "/api/auth/google",
        { method: "POST", body: { credential } },
      );
      storeTokens(data.access, data.refresh);
      await refreshMe();
    },
    [refreshMe],
  );

  const logout = useCallback(() => {
    clearTokens();
    setMe(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ me, loading, googleClientId, loginWithCredential, refreshMe, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}
