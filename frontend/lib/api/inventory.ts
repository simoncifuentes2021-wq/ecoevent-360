import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { InventoryItem, InventoryItemCreate, InventoryItemUpdate } from "@/types/inventory";

export function getInventoryItems(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<InventoryItem>>(`/inventory/items${toQuery(params)}`);
}

export async function getAllInventoryItems(params: Record<string, QueryValue> = {}) {
  const limit = 100;
  const first = await getInventoryItems({ ...params, page: 1, limit });
  const items = [...first.items];
  const pages = Math.ceil(first.total / limit);
  const remaining = await Promise.all(
    Array.from({ length: Math.max(0, pages - 1) }, (_, index) =>
      getInventoryItems({ ...params, page: index + 2, limit })
    )
  );
  items.push(...remaining.flatMap((response) => response.items));
  return items;
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
