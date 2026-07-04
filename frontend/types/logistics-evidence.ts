export type LogisticsEvidenceStage =
  | "LOGISTICS_PREPARATION"
  | "LOGISTICS_LOADING"
  | "LOGISTICS_DISPATCH"
  | "LOGISTICS_DELIVERY"
  | "LOGISTICS_OUTCOME"
  | "LOGISTICS_RETURN"
  | "LOGISTICS_DAMAGED_RETURN"
  | "LOGISTICS_LOSS"
  | "LOGISTICS_DISCARDED"
  | "LOGISTICS_CLOSURE"
  | "PURCHASE_REQUEST"
  | "PURCHASE_RECEIPT"
  | "PURCHASE_WAREHOUSE_RECEIPT"
  | "PURCHASE_DIRECT_EVENT_DELIVERY"
  | "STOCK_ADJUSTMENT"
  | "STOCK_DAMAGE"
  | "STOCK_LOSS"
  | "STOCK_CORRECTION";

export type LogisticsEvidence = {
  id: string;
  event_id: string | null;
  logistics_order_id: string | null;
  logistics_order_item_id: string | null;
  purchase_request_id: string | null;
  purchase_request_item_id: string | null;
  stock_movement_id: string | null;
  warehouse_id: string | null;
  evidence_stage: LogisticsEvidenceStage;
  file_url: string;
  file_key: string | null;
  file_name: string | null;
  file_type: string | null;
  mime_type: string | null;
  size_bytes: number | null;
  notes: string | null;
  uploaded_by: string | null;
  created_at: string;
  updated_at: string;
};
