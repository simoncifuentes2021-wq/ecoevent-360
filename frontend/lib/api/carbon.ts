import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { CarbonRecord, CarbonRecordCreate, CarbonRecordUpdate } from "@/types/carbon";

function normalize(value: CarbonRecord[] | ListResponse<CarbonRecord>): ListResponse<CarbonRecord> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export const getCarbonSummary = (eventId: string) => api.get<unknown>(`/events/${eventId}/carbon-summary`);
export async function getCarbonRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<CarbonRecord[] | ListResponse<CarbonRecord>>(`/events/${eventId}/carbon-records${toQuery(params)}`));
}
export const createCarbonRecord = (eventId: string, data: CarbonRecordCreate) => api.post<CarbonRecord>(`/events/${eventId}/carbon-records`, data);
export const updateCarbonRecord = (recordId: string, data: CarbonRecordUpdate) => api.patch<CarbonRecord>(`/carbon-records/${recordId}`, data);
export const deleteCarbonRecord = (recordId: string) => api.delete<CarbonRecord>(`/carbon-records/${recordId}`);
