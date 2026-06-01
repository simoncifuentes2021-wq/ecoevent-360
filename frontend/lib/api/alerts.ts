import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { Alert, AlertCreate, AlertResolve } from "@/types/alert";
import type { ListResponse } from "@/types/common";

function normalize(value: Alert[] | ListResponse<Alert>): ListResponse<Alert> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export async function getEventAlerts(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<Alert[] | ListResponse<Alert>>(`/events/${eventId}/alerts${toQuery(params)}`));
}

export function createAlert(eventId: string, data: AlertCreate) {
  return api.post<Alert>(`/events/${eventId}/alerts`, data);
}

export function resolveAlert(alertId: string, data: AlertResolve = {}) {
  return api.patch<Alert>(`/alerts/${alertId}/resolve`, data);
}
