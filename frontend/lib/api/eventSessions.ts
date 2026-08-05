import { api } from "@/lib/api";
import type { EventSession, EventSessionCreate, EventSessionStatus, EventSessionUpdate } from "@/types/eventSession";

export function getEventSessions(eventId: string, includeArchived = false) {
  return api.get<EventSession[]>(`/events/${eventId}/sessions?include_archived=${includeArchived}`);
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

export function transitionEventSession(sessionId: string, status: EventSessionStatus) {
  return api.post<EventSession>(`/event-sessions/${sessionId}/transition`, { status });
}

export function archiveEventSession(sessionId: string) {
  return api.post<EventSession>(`/event-sessions/${sessionId}/archive`, {});
}

export function restoreEventSession(sessionId: string) {
  return api.post<EventSession>(`/event-sessions/${sessionId}/restore`, {});
}

export function duplicateEventSession(sessionId: string) {
  return api.post<EventSession>(`/event-sessions/${sessionId}/duplicate`, {});
}

export function reorderEventSessions(eventId: string, sessionIds: string[]) {
  return api.put<EventSession[]>(`/events/${eventId}/sessions/reorder`, { session_ids: sessionIds });
}
