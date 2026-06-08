import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { WasteType, WasteTypeCreate, WasteTypeUpdate } from "@/types/waste";

function normalizeWasteTypes(value: WasteType[] | ListResponse<WasteType>) {
  return Array.isArray(value) ? value : value.items;
}

export async function getWasteTypes() {
  return normalizeWasteTypes(await api.get<WasteType[] | ListResponse<WasteType>>("/waste-types"));
}

export function createWasteType(data: WasteTypeCreate) {
  return api.post<WasteType>("/waste-types", data);
}

export function updateWasteType(id: string, data: WasteTypeUpdate) {
  return api.patch<WasteType>(`/waste-types/${id}`, data);
}

export function deleteWasteType(id: string) {
  return api.delete<WasteType>(`/waste-types/${id}`);
}
