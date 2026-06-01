"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { api } from "@/lib/api";
import {
  clearSession,
  defaultRouteForRole,
  getStoredToken,
  getStoredUser,
  storeSession,
  updateStoredUser
} from "@/lib/auth";
import type { AuthUser, LoginRequest, LoginResponse } from "@/types/auth";
import type { UserRole } from "@/types/roles";

export function useAuth() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    const storedToken = getStoredToken();
    if (!storedToken) {
      setLoading(false);
      return null;
    }
    setToken(storedToken);
    const storedUser = getStoredUser();
    if (storedUser) setUser(storedUser);
    try {
      const current = await api.get<AuthUser>("/auth/me");
      updateStoredUser(current);
      setUser(current);
      return current;
    } catch {
      clearSession();
      setUser(null);
      setToken(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshMe();
  }, [refreshMe]);

  const login = useCallback(
    async (payload: LoginRequest) => {
      const session = await api.post<LoginResponse>("/auth/login", payload, { auth: false });
      storeSession(session);
      setToken(session.access_token);
      setUser(session.user);
      router.push(defaultRouteForRole(session.user.role));
    },
    [router]
  );

  const logout = useCallback(() => {
    clearSession();
    setToken(null);
    setUser(null);
    router.push("/login");
  }, [router]);

  return useMemo(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      refreshMe,
      hasRole: (...roles: UserRole[]) => Boolean(user && roles.includes(user.role))
    }),
    [loading, login, logout, refreshMe, token, user]
  );
}
