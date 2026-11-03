import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "./api";
import type { Role, User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

const Ctx = createContext<AuthState | null>(null);
interface TokenOut { access_token: string; user: User }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const clear = useCallback(() => { tokenStore.set(null); setUser(null); }, []);

  useEffect(() => {
    setUnauthorizedHandler(clear);
    if (!tokenStore.get()) { setLoading(false); return; }
    api.get<User>("/auth/me").then(setUser).catch(clear).finally(() => setLoading(false));
  }, [clear]);

  const accept = (t: TokenOut) => { tokenStore.set(t.access_token); setUser(t.user); };

  const value = useMemo<AuthState>(() => ({
    user, loading,
    login: async (email, password) => accept(await api.post<TokenOut>("/auth/login", { email, password })),
    register: async (email, password, full_name) => accept(await api.post<TokenOut>("/auth/register", { email, password, full_name })),
    logout: async () => { try { await api.post("/auth/logout"); } finally { clear(); } },
    hasRole: (...roles) => !!user && roles.includes(user.role),
  }), [user, loading, clear]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
