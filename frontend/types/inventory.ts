export type InventoryItemType =
  | "RETURNABLE"
  | "CONSUMABLE"
  | "PARTIAL_CONSUMABLE"
  | "DISPOSABLE";

export type InventoryItem = {
  id: string;
  sku: string | null;
  name: string;
  description: string | null;
  item_type: InventoryItemType;
  return_required: boolean;
  unit: string | null;
  unit_price: string | number;
  replacement_cost: string | number | null;
  min_stock: string | number;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

export type InventoryItemCreate = {
  sku?: string | null;
  name: string;
  description?: string | null;
  item_type: InventoryItemType;
  return_required?: boolean | null;
  unit?: string | null;
  unit_price?: number;
  replacement_cost?: number | null;
  min_stock?: number;
};

export type InventoryItemUpdate = Partial<InventoryItemCreate> & {
  is_active?: boolean;
};
