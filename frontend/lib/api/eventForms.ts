import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { EventForm, EventFormCreate, EventFormSummary, EventFormType, FormsSessionComparison, FormResponse } from "@/types/eventForm";

function listFrom<T>(raw: T[] | ListResponse<T> | { items?: T[]; total?: number; page?: number; limit?: number }): ListResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, limit: raw.length };
  const items = raw.items ?? [];
  return { items, total: raw.total ?? items.length, page: raw.page ?? 1, limit: raw.limit ?? items.length };
}

export async function getEventForms(eventId: string, params: Record<string, QueryValue> = {}) {
  const raw = await api.get<EventForm[] | ListResponse<EventForm>>(`/events/${eventId}/forms${toQuery(params)}`);
  return listFrom(raw);
}

export function createEventForm(eventId: string, data: EventFormCreate) {
  return api.post<EventForm>(`/events/${eventId}/forms`, data);
}

export function publishEventForm(formId: string) {
  return api.patch<EventForm>(`/forms/${formId}/publish`, {});
}

export function closeEventForm(formId: string) {
  return api.patch<EventForm>(`/forms/${formId}/close`, {});
}

export function getEventFormSummary(formId: string) {
  return api.get<EventFormSummary>(`/forms/${formId}/summary`);
}

export function getEventFormResponses(formId: string) {
  return api.get<FormResponse[]>(`/forms/${formId}/responses`);
}

export function getFormsSessionComparison(eventId: string, formType?: EventFormType | "") {
  const query = formType ? toQuery({ form_type: formType }) : "";
  return api.get<FormsSessionComparison>(`/events/${eventId}/forms/session-comparison${query}`);
}
