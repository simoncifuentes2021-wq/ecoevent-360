import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { WasteRecord, WasteRecordCreate, WasteRecordUpdate } from "@/types/waste";

function normalize(value: WasteRecord[] | ListResponse<WasteRecord>): ListResponse<WasteRecord> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export function getWasteSummary(eventId: string) {
  return api.get<unknown>(`/events/${eventId}/waste-summary`);
}

export async function getWasteRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<WasteRecord[] | ListResponse<WasteRecord>>(`/events/${eventId}/waste-records${toQuery(params)}`));
}

export function createWasteRecord(eventId: string, data: WasteRecordCreate) {
  return api.post<WasteRecord>(`/events/${eventId}/waste-records`, data);
}

export function updateWasteRecord(recordId: string, data: WasteRecordUpdate) {
  return api.patch<WasteRecord>(`/waste-records/${recordId}`, data);
}

export function deleteWasteRecord(recordId: string) {
  return api.delete<WasteRecord>(`/waste-records/${recordId}`);
}
