import { API_URL } from "@/lib/constants";
import { clearSession, getStoredToken } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { AuditLogFilters, AuditLogListResponse } from "@/types/auditLog";

type QueryParams = Record<string, QueryValue>;

export function getAuditLogs(params: AuditLogFilters = {}) {
  return api.get<AuditLogListResponse>(`/audit-logs${toQuery(params as QueryParams)}`);
}

export function getEventAuditLogs(eventId: string, params: AuditLogFilters = {}) {
  return api.get<AuditLogListResponse>(`/events/${eventId}/audit-logs${toQuery(params as QueryParams)}`);
}

export async function exportAuditLogs(params: AuditLogFilters = {}) {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}/audit-logs/export${toQuery(params as QueryParams)}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });

  if (response.status === 401) {
    clearSession();
    if (typeof window !== "undefined") window.location.href = "/login";
  }

  if (!response.ok) {
    let detail = "No se pudo exportar la auditoria.";
    try {
      const data = (await response.json()) as { detail?: string };
      detail = data.detail || detail;
    } catch {}
    throw new ApiError(response.status, detail);
  }

  return response.blob();
}
