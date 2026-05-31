import { useEffect, useState } from "react";
import { authApi } from "@/api";
import {
  getAccessToken,
  getStoredUser,
  clearAuth,
  subscribeAuth,
  type AuthUser,
} from "@/lib/auth";
import { IS_DEMO_MODE } from "@/lib/env";

/**
 * Returns the current authentication snapshot.
 * Refetches the server-side profile on first auth state change to ensure
 * the stored user record matches what /auth/me reports.
 */
export function useAuth(): {
  user: AuthUser | null;
  token: string | null;
  authenticated: boolean;
  loading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
} {
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser());
  const [token, setToken] = useState<string | null>(() => getAccessToken());
  const [loading, setLoading] = useState<boolean>(Boolean(token));

  useEffect(() => {
    const unsub = subscribeAuth(() => {
      setUser(getStoredUser());
      setToken(getAccessToken());
    });
    return unsub;
  }, []);

  useEffect(() => {
    if (IS_DEMO_MODE || !token) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    authApi
      .me()
      .then((me) => {
        if (!cancelled) setUser((current) => ({ ...(current ?? {}), ...me }));
      })
      .catch(() => {
        /* http layer clears auth on 401 */
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [token]);

  return {
    user,
    token,
    authenticated: Boolean(token),
    loading,
    refresh: async () => {
      if (!token) return;
      const me = await authApi.me().catch(() => null);
      if (me) setUser((current) => ({ ...(current ?? {}), ...me }));
    },
    logout: async () => {
      await authApi.logout().catch(() => clearAuth());
    },
  };
}
