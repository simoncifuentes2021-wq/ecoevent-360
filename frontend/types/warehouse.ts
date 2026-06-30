import type { UserRole } from "@/types/roles";

export type Warehouse = {
  id: string;
  name: string;
  address: string | null;
  city: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type WarehouseCreate = {
  name: string;
  address?: string | null;
  city?: string | null;
  notes?: string | null;
};

export type WarehouseUpdate = Partial<WarehouseCreate> & {
  is_active?: boolean;
};

export type WarehouseUser = {
  id: string;
  warehouse_id: string;
  user_id: string;
  can_view_stock: boolean;
  can_manage_stock: boolean;
  can_dispatch_orders: boolean;
  created_at: string;
  user_full_name: string | null;
  user_email: string | null;
  user_role: UserRole | null;
};

export type WarehouseUserCreate = {
  user_id: string;
  can_view_stock?: boolean;
  can_manage_stock?: boolean;
  can_dispatch_orders?: boolean;
};

export type WarehouseUserUpdate = {
  can_view_stock?: boolean;
  can_manage_stock?: boolean;
  can_dispatch_orders?: boolean;
};

export type MyWarehouseAssignment = {
  id: string;
  warehouse_id: string;
  warehouse_name: string;
  can_view_stock: boolean;
  can_manage_stock: boolean;
  can_dispatch_orders: boolean;
  created_at: string;
};
