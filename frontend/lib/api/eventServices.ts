import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { EventService, EventServiceCreate, EventServiceUpdate } from "@/types/eventService";

function normalizeEventServices(value: EventService[] | ListResponse<EventService> | { data?: EventService[] }) {
  if (Array.isArray(value)) return value;
  if ("items" in value && Array.isArray(value.items)) return value.items;
  if ("data" in value && Array.isArray(value.data)) return value.data;
  return [];
}

export async function getEventServices(eventId: string) {
  const response = await api.get<EventService[] | ListResponse<EventService> | { data?: EventService[] }>(`/events/${eventId}/services`);
  return normalizeEventServices(response);
}

export function createEventService(eventId: string, data: EventServiceCreate) {
  return api.post<EventService>(`/events/${eventId}/services`, data);
}

export function updateEventService(eventId: string, eventServiceId: string, data: EventServiceUpdate) {
  return api.patch<EventService>(`/events/${eventId}/services/${eventServiceId}`, data);
}

export function deleteEventService(eventId: string, eventServiceId: string) {
  return api.delete<EventService>(`/events/${eventId}/services/${eventServiceId}`);
}
