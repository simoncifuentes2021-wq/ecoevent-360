import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type {
  PurchaseRequest,
  PurchaseRequestFromOrderCreate,
  PurchaseRequestMarkPurchased,
  PurchaseRequestReceive,
  PurchaseRequestReject
} from "@/types/purchase-request";

export function getPurchaseRequests(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<PurchaseRequest>>(`/purchase-requests${toQuery(params)}`);
}

export function getPurchaseRequest(id: string) {
  return api.get<PurchaseRequest>(`/purchase-requests/${id}`);
}

export function approvePurchaseRequest(id: string) {
  return api.post<PurchaseRequest>(`/purchase-requests/${id}/approve`, {});
}

export function rejectPurchaseRequest(id: string, data: PurchaseRequestReject) {
  return api.post<PurchaseRequest>(`/purchase-requests/${id}/reject`, data);
}

export function markPurchaseRequestPurchased(id: string, data: PurchaseRequestMarkPurchased) {
  return api.post<PurchaseRequest>(`/purchase-requests/${id}/mark-purchased`, data);
}

export function receivePurchaseRequest(id: string, data: PurchaseRequestReceive) {
  return api.post<PurchaseRequest>(`/purchase-requests/${id}/receive`, data);
}

export function deliverPurchaseRequestDirectToEvent(id: string, data: PurchaseRequestReceive) {
  return api.post<PurchaseRequest>(`/purchase-requests/${id}/deliver-direct-to-event`, data);
}

export function cancelPurchaseRequest(id: string) {
  return api.post<PurchaseRequest>(`/purchase-requests/${id}/cancel`, {});
}

export function createPurchaseRequestFromOrder(orderId: string, data: PurchaseRequestFromOrderCreate) {
  return api.post<PurchaseRequest>(`/logistics-orders/${orderId}/purchase-request`, data);
}

export function getPurchaseRequestsForOrder(orderId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<PurchaseRequest>>(`/logistics-orders/${orderId}/purchase-requests${toQuery(params)}`);
}
