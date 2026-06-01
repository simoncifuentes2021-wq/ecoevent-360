import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { Zone, ZoneCreate, ZoneUpdate } from "@/types/zone";

function normalizeZones(value: Zone[] | ListResponse<Zone> | { data?: Zone[] }) {
  if (Array.isArray(value)) return value;
  if ("items" in value && Array.isArray(value.items)) return value.items;
  if ("data" in value && Array.isArray(value.data)) return value.data;
  return [];
}

export async function getEventZones(eventId: string) {
  const response = await api.get<Zone[] | ListResponse<Zone> | { data?: Zone[] }>(`/events/${eventId}/zones`);
  return normalizeZones(response);
}

export function createEventZone(eventId: string, data: ZoneCreate) {
  return api.post<Zone>(`/events/${eventId}/zones`, data);
}

export function updateZone(zoneId: string, data: ZoneUpdate) {
  return api.patch<Zone>(`/zones/${zoneId}`, data);
}

export function deleteZone(zoneId: string) {
  return api.delete<Zone>(`/zones/${zoneId}`);
}
