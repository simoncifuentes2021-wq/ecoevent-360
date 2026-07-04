export type PurchaseRequestStatus =
  | "REQUESTED"
  | "APPROVED"
  | "REJECTED"
  | "PURCHASED"
  | "PARTIALLY_RECEIVED"
  | "RECEIVED"
  | "DELIVERED_DIRECT_TO_EVENT"
  | "CANCELLED";

export type PurchaseDeliveryMode = "TO_WAREHOUSE" | "DIRECT_TO_EVENT";

export type PurchaseEntity = {
  id: string;
  name?: string | null;
  title?: string | null;
  full_name?: string | null;
  email?: string | null;
};

export type PurchaseRequestItem = {
  id: string;
  purchase_request_id: string;
  logistics_order_item_id: string | null;
  item_id: string;
  item_name_snapshot: string;
  unit_snapshot: string | null;
  quantity_requested: string | number;
  quantity_purchased: string | number;
  quantity_received: string | number;
  unit_price_estimated: string | number;
  unit_price_purchased: string | number;
  total_estimated: string | number;
  total_purchased: string | number;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type PurchaseRequest = {
  id: string;
  event_id: string | null;
  logistics_order_id: string | null;
  requested_by: string | null;
  approved_by: string | null;
  purchased_by: string | null;
  received_by: string | null;
  warehouse_id: string | null;
  status: PurchaseRequestStatus;
  delivery_mode: PurchaseDeliveryMode;
  title: string;
  description: string | null;
  notes: string | null;
  rejection_reason: string | null;
  requested_at: string;
  approved_at: string | null;
  rejected_at: string | null;
  purchased_at: string | null;
  received_at: string | null;
  cancelled_at: string | null;
  total_estimated_amount: string | number;
  total_purchased_amount: string | number;
  created_at: string;
  updated_at: string;
  event: PurchaseEntity | null;
  logistics_order: PurchaseEntity | null;
  warehouse: PurchaseEntity | null;
  requester: PurchaseEntity | null;
  approver: PurchaseEntity | null;
  purchaser: PurchaseEntity | null;
  receiver: PurchaseEntity | null;
  items: PurchaseRequestItem[];
};

export type PurchaseRequestFromOrderCreate = {
  title: string;
  delivery_mode: PurchaseDeliveryMode;
  warehouse_id?: string | null;
  notes?: string | null;
};

export type PurchaseRequestReject = {
  rejection_reason: string;
};

export type PurchaseRequestMarkPurchased = {
  items: Array<{
    purchase_request_item_id: string;
    quantity_purchased: number;
    unit_price_purchased: number;
  }>;
  notes?: string | null;
};

export type PurchaseRequestReceive = {
  items: Array<{
    purchase_request_item_id: string;
    quantity_received: number;
  }>;
  notes?: string | null;
};
