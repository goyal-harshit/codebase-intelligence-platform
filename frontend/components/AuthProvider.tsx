"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  AuthUser,
  getMe,
  getToken,
  login as apiLogin,
  logout as apiLogout,
  register as apiRegister,
  setToken,
} from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await getMe());
    } catch {
      // Token expired or invalid — drop it so the UI reflects a signed-out state.
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      await apiLogin(email, password);
      await refresh();
    },
    [refresh]
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      await apiRegister(email, password, fullName);
      // FastAPI-Users registration doesn't return a token, so sign in right after.
      await apiLogin(email, password);
      await refresh();
    },
    [refresh]
  );

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
