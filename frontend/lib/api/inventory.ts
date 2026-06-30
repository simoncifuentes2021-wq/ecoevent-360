import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { InventoryItem, InventoryItemCreate, InventoryItemUpdate } from "@/types/inventory";

export function getInventoryItems(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<InventoryItem>>(`/inventory/items${toQuery(params)}`);
}

export function getInventoryItem(id: string) {
  return api.get<InventoryItem>(`/inventory/items/${id}`);
}

export function createInventoryItem(data: InventoryItemCreate) {
  return api.post<InventoryItem>("/inventory/items", data);
}

export function updateInventoryItem(id: string, data: InventoryItemUpdate) {
  return api.patch<InventoryItem>(`/inventory/items/${id}`, data);
}

export function deactivateInventoryItem(id: string) {
  return api.delete<InventoryItem>(`/inventory/items/${id}`);
}
