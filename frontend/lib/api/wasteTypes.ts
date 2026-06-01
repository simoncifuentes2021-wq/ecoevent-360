import { api } from "@/lib/api";
import type { WasteType, WasteTypeCreate, WasteTypeUpdate } from "@/types/waste";

export function getWasteTypes() {
  return api.get<WasteType[]>("/waste-types");
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
