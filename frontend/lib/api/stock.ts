import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type {
  StockBalance,
  StockBalanceCreate,
  StockBalanceUpdate,
  StockMovement,
  StockMovementCreate
} from "@/types/stock";

export function getStockBalances(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<StockBalance>>(`/stock${toQuery(params)}`);
}

export function getStockBalance(id: string) {
  return api.get<StockBalance>(`/stock/${id}`);
}

export function createStockBalance(data: StockBalanceCreate) {
  return api.post<StockBalance>("/stock", data);
}

export function updateStockBalance(id: string, data: StockBalanceUpdate) {
  return api.patch<StockBalance>(`/stock/${id}`, data);
}

export function getStockMovements(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<StockMovement>>(`/stock/movements${toQuery(params)}`);
}

export function getStockMovement(id: string) {
  return api.get<StockMovement>(`/stock/movements/${id}`);
}

export function createStockMovement(data: StockMovementCreate) {
  return api.post<StockMovement>("/stock/movements", data);
}

export function getStockBalanceMovements(stockId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<StockMovement>>(`/stock/${stockId}/movements${toQuery(params)}`);
}

export function getWarehouseStock(warehouseId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<StockBalance>>(`/warehouses/${warehouseId}/stock${toQuery(params)}`);
}

export function getInventoryItemStock(itemId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<StockBalance>>(`/inventory/items/${itemId}/stock${toQuery(params)}`);
}
