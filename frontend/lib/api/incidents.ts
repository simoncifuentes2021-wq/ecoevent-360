import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Incident, IncidentCreate, IncidentResolve, IncidentUpdate } from "@/types/incident";

function normalize(value: Incident[] | ListResponse<Incident>): ListResponse<Incident> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export async function getEventIncidents(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<Incident[] | ListResponse<Incident>>(`/events/${eventId}/incidents${toQuery(params)}`));
}

export function createIncident(eventId: string, data: IncidentCreate) {
  return api.post<Incident>(`/events/${eventId}/incidents`, data);
}

export function getIncident(incidentId: string) {
  return api.get<Incident>(`/incidents/${incidentId}`);
}

export function updateIncident(incidentId: string, data: IncidentUpdate) {
  return api.patch<Incident>(`/incidents/${incidentId}`, data);
}

export function resolveIncident(incidentId: string, data: IncidentResolve) {
  return api.patch<Incident>(`/incidents/${incidentId}/resolve`, data);
}

export function closeIncident(incidentId: string) {
  return api.patch<Incident>(`/incidents/${incidentId}/close`, {});
}
