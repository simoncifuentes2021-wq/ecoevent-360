import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Survey, SurveyCreate, SurveyUpdate } from "@/types/survey";

function listFrom<T>(raw: T[] | ListResponse<T> | { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number }): ListResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, limit: raw.length };
  const value = raw as { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number };
  const items = value.items ?? value.data ?? [];
  return { items, total: value.total ?? items.length, page: value.page ?? 1, limit: value.limit ?? items.length };
}

export async function getEventSurveys(eventId: string, params: Record<string, QueryValue> = {}) {
  const raw = await api.get<Survey[] | ListResponse<Survey>>(`/events/${eventId}/surveys${toQuery(params)}`);
  return listFrom(raw);
}

export function createSurvey(eventId: string, data: SurveyCreate) {
  return api.post<Survey>(`/events/${eventId}/surveys`, data);
}

export function getSurvey(surveyId: string) {
  return api.get<Survey>(`/surveys/${surveyId}`);
}

export function updateSurvey(surveyId: string, data: SurveyUpdate) {
  return api.patch<Survey>(`/surveys/${surveyId}`, data);
}

export function closeSurvey(surveyId: string) {
  return api.patch<Survey>(`/surveys/${surveyId}/close`, {});
}
