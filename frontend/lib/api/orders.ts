import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type {
  CatalogItem,
  CatalogItemCreate,
  EventOrder,
  EventOrderCreate,
  EventOrderItem,
  EventOrderItemCreate,
  EventOrderItemUpdate,
  EventOrderUpdate,
  OrderEvidence,
  OrderEvidenceStage,
  OrderItemStageStatus,
  OrderStatus
} from "@/types/order";

export function getCatalogItems(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<CatalogItem>>(`/catalog-items${toQuery(params)}`);
}

export function createCatalogItem(data: CatalogItemCreate) {
  return api.post<CatalogItem>("/catalog-items", data);
}

export function updateCatalogItem(id: string, data: Partial<CatalogItemCreate>) {
  return api.patch<CatalogItem>(`/catalog-items/${id}`, data);
}

export function deactivateCatalogItem(id: string) {
  return api.delete<CatalogItem>(`/catalog-items/${id}`);
}

export function getEventOrders(eventId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<EventOrder>>(`/events/${eventId}/orders${toQuery(params)}`);
}

export function createEventOrder(eventId: string, data: EventOrderCreate) {
  return api.post<EventOrder>(`/events/${eventId}/orders`, data);
}

export function getOrder(id: string) {
  return api.get<EventOrder>(`/orders/${id}`);
}

export function updateOrder(id: string, data: EventOrderUpdate) {
  return api.patch<EventOrder>(`/orders/${id}`, data);
}

export function updateOrderStatus(id: string, status: OrderStatus) {
  return api.patch<EventOrder>(`/orders/${id}/status`, { status });
}

export function cancelOrder(id: string) {
  return api.delete<EventOrder>(`/orders/${id}`);
}

export function getMyOrders(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<EventOrder>>(`/me/orders${toQuery(params)}`);
}

export function createOrderItem(orderId: string, data: EventOrderItemCreate) {
  return api.post<EventOrderItem>(`/orders/${orderId}/items`, data);
}

export function updateOrderItem(orderId: string, itemId: string, data: EventOrderItemUpdate) {
  return api.patch<EventOrderItem>(`/orders/${orderId}/items/${itemId}`, data);
}

export function deleteOrderItem(orderId: string, itemId: string) {
  return api.delete<void>(`/orders/${orderId}/items/${itemId}`);
}

export function markOrderItemStage(itemId: string, stage: OrderEvidenceStage, status: OrderItemStageStatus = "COMPLETED", observation?: string | null) {
  const endpoint = stage === "LOAD" ? "load" : stage === "DELIVERY" ? "deliver" : "return";
  return api.patch<EventOrderItem>(`/order-items/${itemId}/${endpoint}`, { status, observation: observation || null });
}

export function getOrderEvidences(orderId: string, params: Record<string, QueryValue> = {}) {
  return api.get<OrderEvidence[]>(`/orders/${orderId}/evidences${toQuery(params)}`);
}

export function uploadOrderEvidence(orderId: string, data: { file: File; stage: OrderEvidenceStage; order_item_id?: string | null; description?: string | null; visible_to_client?: boolean }) {
  const form = new FormData();
  form.append("file", data.file);
  form.append("stage", data.stage);
  if (data.order_item_id) form.append("order_item_id", data.order_item_id);
  if (data.description) form.append("description", data.description);
  if (data.visible_to_client !== undefined) form.append("visible_to_client", String(data.visible_to_client));
  return api.post<OrderEvidence>(`/orders/${orderId}/evidences`, form);
}

export function deleteOrderEvidence(id: string) {
  return api.delete<void>(`/order-evidences/${id}`);
}
