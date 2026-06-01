import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { FuelRecord, FuelRecordCreate, FuelRecordUpdate } from "@/types/operations";

function normalize(value: FuelRecord[] | ListResponse<FuelRecord>): ListResponse<FuelRecord> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}
export async function getFuelRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<FuelRecord[] | ListResponse<FuelRecord>>(`/events/${eventId}/fuel-records${toQuery(params)}`));
}
export const createFuelRecord = (eventId: string, data: FuelRecordCreate) => api.post<FuelRecord>(`/events/${eventId}/fuel-records`, data);
export const updateFuelRecord = (id: string, data: FuelRecordUpdate) => api.patch<FuelRecord>(`/fuel-records/${id}`, data);
export const deleteFuelRecord = (id: string) => api.delete<FuelRecord>(`/fuel-records/${id}`);
