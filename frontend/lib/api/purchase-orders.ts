import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { PurchaseOrder, PurchaseOrderInput } from "@/types/purchase-order";
import { toQuery } from "@/lib/api/query";
import { API_URL } from "@/lib/constants";
import { getStoredToken } from "@/lib/auth";

export function getPurchaseOrders(params: Record<string, string | number | undefined> = {}) {
  return api.get<ListResponse<PurchaseOrder>>(`/purchase-orders${toQuery(params)}`);
}
export function createPurchaseOrder(data: PurchaseOrderInput) { return api.post<PurchaseOrder>("/purchase-orders", data); }
export function updatePurchaseOrder(id: string, data: PurchaseOrderInput) { return api.put<PurchaseOrder>(`/purchase-orders/${id}`, data); }
export function approvePurchaseOrder(id: string) { return api.post<PurchaseOrder>(`/purchase-orders/${id}/approve`, {}); }
export function sendPurchaseOrder(id: string) { return api.post<PurchaseOrder>(`/purchase-orders/${id}/send`, {}); }
export function receivePurchaseOrder(id: string, items: Array<{ item_id: string; received_quantity: number }>, notes?: string) { return api.post<PurchaseOrder>(`/purchase-orders/${id}/receive`, { items, notes }); }
export function cancelPurchaseOrder(id: string, reason: string) { return api.post<PurchaseOrder>(`/purchase-orders/${id}/cancel`, { reason }); }
export async function getPurchaseOrderPdf(id: string) {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}/purchase-orders/${id}/pdf`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) throw new Error("No se pudo preparar el PDF de la orden.");
  return response.blob();
}
