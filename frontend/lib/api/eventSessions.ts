import { api } from "@/lib/api";
import type { EventSession, EventSessionCreate, EventSessionUpdate } from "@/types/eventSession";

export function getEventSessions(eventId: string) {
  return api.get<EventSession[]>(`/events/${eventId}/sessions`);
}

export function createEventSession(eventId: string, data: EventSessionCreate) {
  return api.post<EventSession>(`/events/${eventId}/sessions`, data);
}

export function updateEventSession(sessionId: string, data: EventSessionUpdate) {
  return api.patch<EventSession>(`/event-sessions/${sessionId}`, data);
}

export function deleteEventSession(sessionId: string) {
  return api.delete<void>(`/event-sessions/${sessionId}`);
}
