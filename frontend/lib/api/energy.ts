import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { EnergyRecord, EnergyRecordCreate, EnergyRecordUpdate } from "@/types/operations";

function normalize(value: EnergyRecord[] | ListResponse<EnergyRecord>): ListResponse<EnergyRecord> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}
export async function getEnergyRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<EnergyRecord[] | ListResponse<EnergyRecord>>(`/events/${eventId}/energy-records${toQuery(params)}`));
}
export const createEnergyRecord = (eventId: string, data: EnergyRecordCreate) => api.post<EnergyRecord>(`/events/${eventId}/energy-records`, data);
export const updateEnergyRecord = (id: string, data: EnergyRecordUpdate) => api.patch<EnergyRecord>(`/energy-records/${id}`, data);
export const deleteEnergyRecord = (id: string) => api.delete<EnergyRecord>(`/energy-records/${id}`);
