import type { AuthUser, LoginResponse } from "@/types/auth";
import type { UserRole } from "@/types/roles";

const TOKEN_KEY = "ecoevent360.access_token";
const USER_KEY = "ecoevent360.user";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function storeSession(session: LoginResponse) {
  window.localStorage.setItem(TOKEN_KEY, session.access_token);
  window.localStorage.setItem(USER_KEY, JSON.stringify(session.user));
}

export function updateStoredUser(user: AuthUser) {
  window.localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(USER_KEY);
}

export function defaultRouteForRole(role: UserRole) {
  if (role === "CLIENT") return "/client/mis-eventos";
  if (role === "SUPERVISOR") return "/supervisor/eventos";
  if (role === "LOGISTICS_OPERATOR") return "/logistica/dashboard";
  if (role === "WORKER") return "/worker/mis-tareas";
  return "/admin/dashboard";
}
