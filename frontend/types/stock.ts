import type { InventoryItemType } from "@/types/inventory";

export type StockBalance = {
  id: string;
  warehouse_id: string;
  warehouse_name: string;
  item_id: string;
  item_name: string;
  item_type: InventoryItemType;
  unit: string | null;
  quantity_on_hand: string | number;
  quantity_reserved: string | number;
  quantity_damaged: string | number;
  available_quantity: string | number;
  min_stock: string | number;
  is_low_stock: boolean;
  unit_price: string | number;
  estimated_stock_value: string | number;
  created_at: string;
  updated_at: string;
};

export type StockBalanceCreate = {
  warehouse_id: string;
  item_id: string;
  quantity_on_hand?: number;
  quantity_reserved?: number;
  quantity_damaged?: number;
};

export type StockBalanceUpdate = Partial<
  Pick<StockBalanceCreate, "quantity_on_hand" | "quantity_reserved" | "quantity_damaged">
>;

export type StockMovementType =
  | "INITIAL_STOCK"
  | "ADJUSTMENT_IN"
  | "ADJUSTMENT_OUT"
  | "DAMAGE"
  | "LOSS"
  | "RECOVER_DAMAGED"
  | "CORRECTION"
  | "PURCHASE_IN"
  | "RESERVE"
  | "UNRESERVE"
  | "OUT_TO_EVENT"
  | "RETURN_FROM_EVENT";

export type StockMovement = {
  id: string;
  warehouse_id: string;
  warehouse_name: string;
  item_id: string;
  item_name: string;
  item_type: InventoryItemType;
  stock_balance_id: string | null;
  movement_type: StockMovementType;
  quantity: string | number;
  previous_quantity_on_hand: string | number | null;
  new_quantity_on_hand: string | number | null;
  previous_quantity_reserved: string | number | null;
  new_quantity_reserved: string | number | null;
  previous_quantity_damaged: string | number | null;
  new_quantity_damaged: string | number | null;
  reference_type: string | null;
  reference_id: string | null;
  reason: string | null;
  notes: string | null;
  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
};

export type StockMovementCreate = {
  warehouse_id: string;
  item_id: string;
  movement_type: StockMovementType;
  quantity: number;
  quantity_on_hand?: number | null;
  quantity_reserved?: number | null;
  quantity_damaged?: number | null;
  reference_type?: string | null;
  reference_id?: string | null;
  reason?: string | null;
  notes?: string | null;
};
