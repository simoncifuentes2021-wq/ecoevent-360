import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type {
  LogisticsOrder,
  LogisticsOrderClose,
  LogisticsOrderCreate,
  LogisticsOrderDeliveryConfirm,
  LogisticsOrderDispatch,
  LogisticsOrderItem,
  LogisticsOrderItemCreate,
  LogisticsOrderItemDeliver,
  LogisticsOrderItemLoad,
  LogisticsOrderItemOutcome,
  LogisticsOrderOutcomeConfirm,
  LogisticsOrderStockCheck,
  LogisticsOrderUpdate
} from "@/types/logistics-order";

export function createEventLogisticsOrder(eventId: string, data: LogisticsOrderCreate) {
  return api.post<LogisticsOrder>(`/events/${eventId}/logistics-orders`, data);
}

export function getEventLogisticsOrders(eventId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<LogisticsOrder>>(`/events/${eventId}/logistics-orders${toQuery(params)}`);
}

export function getLogisticsOrders(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<LogisticsOrder>>(`/logistics-orders${toQuery(params)}`);
}

export function getMyLogisticsOrders(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<LogisticsOrder>>(`/me/logistics-orders${toQuery(params)}`);
}

export function getLogisticsOrder(id: string) {
  return api.get<LogisticsOrder>(`/logistics-orders/${id}`);
}

export function checkLogisticsOrderStock(id: string) {
  return api.get<LogisticsOrderStockCheck>(`/logistics-orders/${id}/stock-check`);
}

export function reserveLogisticsOrderStock(id: string) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/reserve`, {});
}

export function unreserveLogisticsOrderStock(id: string) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/unreserve`, {});
}

export function startLogisticsOrderPreparation(id: string) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/start-preparation`, {});
}

export function loadLogisticsOrderItem(id: string, data: LogisticsOrderItemLoad) {
  return api.patch<LogisticsOrderItem>(`/logistics-order-items/${id}/load`, data);
}

export function dispatchLogisticsOrder(id: string, data: LogisticsOrderDispatch) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/dispatch`, data);
}

export function deliverLogisticsOrderItem(id: string, data: LogisticsOrderItemDeliver) {
  return api.patch<LogisticsOrderItem>(`/logistics-order-items/${id}/deliver`, data);
}

export function confirmLogisticsOrderDelivery(id: string, data: LogisticsOrderDeliveryConfirm) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/confirm-delivery`, data);
}

export function registerLogisticsOrderItemOutcome(id: string, data: LogisticsOrderItemOutcome) {
  return api.patch<LogisticsOrderItem>(`/logistics-order-items/${id}/outcome`, data);
}

export function confirmLogisticsOrderOutcome(id: string, data: LogisticsOrderOutcomeConfirm) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/confirm-outcome`, data);
}

export function closeLogisticsOrder(id: string, data: LogisticsOrderClose) {
  return api.post<LogisticsOrder>(`/logistics-orders/${id}/close`, data);
}

export function updateLogisticsOrder(id: string, data: LogisticsOrderUpdate) {
  return api.patch<LogisticsOrder>(`/logistics-orders/${id}`, data);
}

export function assignLogisticsOrder(id: string, assigned_operator_id: string) {
  return api.patch<LogisticsOrder>(`/logistics-orders/${id}/assign`, { assigned_operator_id });
}

export function cancelLogisticsOrder(id: string) {
  return api.patch<LogisticsOrder>(`/logistics-orders/${id}/cancel`, {});
}

export function addLogisticsOrderItem(orderId: string, data: LogisticsOrderItemCreate) {
  return api.post<LogisticsOrderItem>(`/logistics-orders/${orderId}/items`, data);
}

export function updateLogisticsOrderItem(itemId: string, data: Partial<LogisticsOrderItemCreate>) {
  return api.patch<LogisticsOrderItem>(`/logistics-order-items/${itemId}`, data);
}

export function deleteLogisticsOrderItem(itemId: string) {
  return api.delete<void>(`/logistics-order-items/${itemId}`);
}
