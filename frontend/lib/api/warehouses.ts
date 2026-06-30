import { ApiError, api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type {
  Warehouse,
  WarehouseCreate,
  MyWarehouseAssignment,
  WarehouseUpdate,
  WarehouseUser,
  WarehouseUserCreate,
  WarehouseUserUpdate
} from "@/types/warehouse";

export function getWarehouses(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<Warehouse>>(`/warehouses${toQuery(params)}`);
}

export function getWarehouse(id: string) {
  return api.get<Warehouse>(`/warehouses/${id}`);
}

export function getMyWarehouseAssignments() {
  return api.get<MyWarehouseAssignment[]>("/warehouses/me/assignments").catch(async (error) => {
    if (error instanceof ApiError && error.status === 404) {
      throw new ApiError(
        404,
        "El backend no tiene activo /warehouses/me/assignments. Reinicia el backend para cargar los permisos de bodega."
      );
    }
    throw error;
  });
}

export function createWarehouse(data: WarehouseCreate) {
  return api.post<Warehouse>("/warehouses", data);
}

export function updateWarehouse(id: string, data: WarehouseUpdate) {
  return api.patch<Warehouse>(`/warehouses/${id}`, data);
}

export function deactivateWarehouse(id: string) {
  return api.delete<Warehouse>(`/warehouses/${id}`);
}

export function getWarehouseUsers(warehouseId: string) {
  return api.get<WarehouseUser[]>(`/warehouses/${warehouseId}/users`);
}

export function assignWarehouseUser(warehouseId: string, data: WarehouseUserCreate) {
  return api.post<WarehouseUser>(`/warehouses/${warehouseId}/users`, data);
}

export function removeWarehouseUser(warehouseId: string, userId: string) {
  return api.delete<void>(`/warehouses/${warehouseId}/users/${userId}`);
}

export function updateWarehouseUser(warehouseId: string, userId: string, data: WarehouseUserUpdate) {
  return api.patch<WarehouseUser>(`/warehouses/${warehouseId}/users/${userId}`, data);
}
