import type { InventoryItemType } from "@/types/inventory";

export type LogisticsOrderStatus =
  | "REQUESTED"
  | "ASSIGNED"
  | "STOCK_REVIEW"
  | "RESERVED"
  | "INSUFFICIENT_STOCK"
  | "IN_PREPARATION"
  | "LOADED"
  | "OUT_OF_WAREHOUSE"
  | "OBSERVED"
  | "CANCELLED";

export type LogisticsOrderUser = {
  id: string;
  full_name: string;
  email: string;
};

export type LogisticsOrderEvent = {
  id: string;
  name: string;
};

export type LogisticsOrderWarehouse = {
  id: string;
  name: string;
};

export type LogisticsOrderItem = {
  id: string;
  order_id: string;
  item_id: string;
  item_name_snapshot: string;
  item_type_snapshot: InventoryItemType | string;
  unit_snapshot: string | null;
  quantity_requested: string | number;
  quantity_reserved: string | number;
  quantity_missing: string | number;
  reservation_status: "PENDING" | "RESERVED" | "INSUFFICIENT_STOCK" | string | null;
  quantity_loaded: string | number;
  quantity_dispatched: string | number;
  preparation_status: "PENDING" | "LOADED" | "PARTIALLY_LOADED" | string;
  unit_price_snapshot: string | number;
  total_price: string | number;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type LogisticsOrder = {
  id: string;
  event_id: string;
  warehouse_id: string;
  requested_by: string;
  assigned_operator_id: string;
  status: LogisticsOrderStatus;
  title: string;
  description: string | null;
  delivery_zone: string | null;
  delivery_notes: string | null;
  total_estimated_amount: string | number;
  reserved_at: string | null;
  reserved_by: string | null;
  prepared_at: string | null;
  prepared_by: string | null;
  dispatched_at: string | null;
  dispatched_by: string | null;
  dispatch_notes: string | null;
  created_at: string;
  updated_at: string;
  event: LogisticsOrderEvent | null;
  warehouse: LogisticsOrderWarehouse | null;
  requester: LogisticsOrderUser | null;
  assigned_operator: LogisticsOrderUser | null;
  items: LogisticsOrderItem[];
};

export type LogisticsOrderItemCreate = {
  item_id: string;
  quantity_requested: number;
  notes?: string | null;
};

export type LogisticsOrderCreate = {
  warehouse_id: string;
  assigned_operator_id: string;
  title: string;
  description?: string | null;
  delivery_zone?: string | null;
  delivery_notes?: string | null;
  items: LogisticsOrderItemCreate[];
};

export type LogisticsOrderUpdate = Partial<
  Pick<LogisticsOrderCreate, "warehouse_id" | "title" | "description" | "delivery_zone" | "delivery_notes">
> & {
  status?: LogisticsOrderStatus;
};

export type LogisticsOrderStockCheckItem = {
  item_id: string;
  item_name_snapshot: string;
  quantity_requested: string | number;
  quantity_reserved: string | number;
  warehouse_id: string;
  warehouse_name: string;
  quantity_on_hand: string | number;
  quantity_reserved_in_stock: string | number;
  quantity_damaged: string | number;
  available_quantity: string | number;
  missing_quantity: string | number;
  can_reserve: boolean;
};

export type LogisticsOrderStockCheck = {
  order_id: string;
  status: LogisticsOrderStatus;
  warehouse_id: string;
  warehouse_name: string;
  can_reserve_all: boolean;
  items: LogisticsOrderStockCheckItem[];
};

export type LogisticsOrderItemLoad = {
  quantity_loaded: number;
  notes?: string | null;
};

export type LogisticsOrderDispatch = {
  dispatch_notes?: string | null;
};
