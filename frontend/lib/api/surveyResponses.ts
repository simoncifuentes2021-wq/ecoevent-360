import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { CSVImportResult, SurveyResponse, SurveySummary } from "@/types/survey";

function listFrom<T>(raw: T[] | ListResponse<T> | { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number }): ListResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, limit: raw.length };
  const value = raw as { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number };
  const items = value.items ?? value.data ?? [];
  return { items, total: value.total ?? items.length, page: value.page ?? 1, limit: value.limit ?? items.length };
}

export function importSurveyResponsesCsv(surveyId: string, fileOrFormData: File | FormData) {
  const formData = fileOrFormData instanceof FormData ? fileOrFormData : new FormData();
  if (fileOrFormData instanceof File) formData.set("file", fileOrFormData);
  return api.post<CSVImportResult>(`/surveys/${surveyId}/responses/import-csv`, formData);
}

export async function getSurveyResponses(surveyId: string, params: Record<string, QueryValue> = {}) {
  const raw = await api.get<SurveyResponse[] | ListResponse<SurveyResponse>>(`/surveys/${surveyId}/responses${toQuery(params)}`);
  return listFrom(raw);
}

export function getSurveySummary(surveyId: string) {
  return api.get<SurveySummary | Record<string, unknown>>(`/surveys/${surveyId}/summary`);
}
