import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { EventStaff, EventStaffCreate } from "@/types/staff";

function normalizeStaff(value: EventStaff[] | ListResponse<EventStaff> | { data?: EventStaff[] }) {
  if (Array.isArray(value)) return value;
  if ("items" in value && Array.isArray(value.items)) return value.items;
  if ("data" in value && Array.isArray(value.data)) return value.data;
  return [];
}

export async function getEventStaff(eventId: string) {
  const response = await api.get<EventStaff[] | ListResponse<EventStaff> | { data?: EventStaff[] }>(`/events/${eventId}/staff`);
  return normalizeStaff(response);
}

export function assignEventStaff(eventId: string, data: EventStaffCreate) {
  return api.post<EventStaff>(`/events/${eventId}/staff`, data);
}

export function removeEventStaff(eventId: string, userId: string) {
  return api.delete<EventStaff>(`/events/${eventId}/staff/${userId}`);
}
