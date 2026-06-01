import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Evidence } from "@/types/evidence";

function normalize(value: Evidence[] | ListResponse<Evidence>): ListResponse<Evidence> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export async function getEventEvidences(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<Evidence[] | ListResponse<Evidence>>(`/events/${eventId}/evidences${toQuery(params)}`));
}

export function createEvidence(formData: FormData) {
  return api.post<Evidence>("/evidences", formData);
}

export function getEvidence(evidenceId: string) {
  return api.get<Evidence>(`/evidences/${evidenceId}`);
}

export function deleteEvidence(evidenceId: string) {
  return api.delete<Evidence>(`/evidences/${evidenceId}`);
}
