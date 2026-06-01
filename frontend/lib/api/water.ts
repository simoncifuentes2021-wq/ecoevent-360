import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { WaterRecord, WaterRecordCreate, WaterRecordUpdate } from "@/types/operations";

function normalize(value: WaterRecord[] | ListResponse<WaterRecord>): ListResponse<WaterRecord> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}
export async function getWaterRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<WaterRecord[] | ListResponse<WaterRecord>>(`/events/${eventId}/water-records${toQuery(params)}`));
}
export const createWaterRecord = (eventId: string, data: WaterRecordCreate) => api.post<WaterRecord>(`/events/${eventId}/water-records`, data);
export const updateWaterRecord = (id: string, data: WaterRecordUpdate) => api.patch<WaterRecord>(`/water-records/${id}`, data);
export const deleteWaterRecord = (id: string) => api.delete<WaterRecord>(`/water-records/${id}`);
