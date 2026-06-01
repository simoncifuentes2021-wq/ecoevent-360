import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { CarbonFactor, CarbonFactorCreate, CarbonFactorUpdate } from "@/types/carbon";

function normalize(value: CarbonFactor[] | ListResponse<CarbonFactor>): ListResponse<CarbonFactor> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 100 };
  return value;
}

export async function getCarbonFactors(params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<CarbonFactor[] | ListResponse<CarbonFactor>>(`/carbon-factors${toQuery(params)}`));
}
export const createCarbonFactor = (data: CarbonFactorCreate) => api.post<CarbonFactor>("/carbon-factors", data);
export const updateCarbonFactor = (id: string, data: CarbonFactorUpdate) => api.patch<CarbonFactor>(`/carbon-factors/${id}`, data);
export const deleteCarbonFactor = (id: string) => api.delete<CarbonFactor>(`/carbon-factors/${id}`);
