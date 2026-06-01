import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Service, ServiceCreate, ServiceUpdate } from "@/types/service";

export function getServices(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<Service>>(`/services${toQuery(params)}`);
}

export function getService(id: string) {
  return api.get<Service>(`/services/${id}`);
}

export function createService(data: ServiceCreate) {
  return api.post<Service>("/services", data);
}

export function updateService(id: string, data: ServiceUpdate) {
  return api.patch<Service>(`/services/${id}`, data);
}

export function deleteService(id: string) {
  return api.delete<Service>(`/services/${id}`);
}
