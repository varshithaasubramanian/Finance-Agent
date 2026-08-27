import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import * as api from "../services/api";
import type { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  error: string | null;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadCurrentUser = useCallback(async () => {
    const token = api.getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.getMe();
      setUser(me);
    } catch {
      api.clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
    const handleUnauthorized = () => setUser(null);
    window.addEventListener("finch:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("finch:unauthorized", handleUnauthorized);
  }, [loadCurrentUser]);

  async function login(email: string, password: string) {
    setError(null);
    try {
      const res = await api.login(email, password);
      api.setToken(res.access_token);
      setUser(res.user);
    } catch (err: any) {
      setError(err.message || "Login failed");
      throw err;
    }
  }

  async function signup(name: string, email: string, password: string) {
    setError(null);
    try {
      const res = await api.signup(name, email, password);
      api.setToken(res.access_token);
      setUser(res.user);
    } catch (err: any) {
      setError(err.message || "Signup failed");
      throw err;
    }
  }

  function logout() {
    api.clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout, error }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
