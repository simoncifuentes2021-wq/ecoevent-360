import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Event, EventCreate, EventStatus, EventUpdate } from "@/types/event";

export function getEvents(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<Event>>(`/events${toQuery(params)}`);
}

export function getEvent(id: string) {
  return api.get<Event>(`/events/${id}`);
}

export function createEvent(data: EventCreate) {
  return api.post<Event>("/events", data);
}

export function updateEvent(id: string, data: EventUpdate) {
  return api.patch<Event>(`/events/${id}`, data);
}

export function changeEventStatus(id: string, status: EventStatus) {
  return api.patch<Event>(`/events/${id}/status`, { status });
}

export function deleteEvent(id: string) {
  return api.delete<Event>(`/events/${id}`);
}
