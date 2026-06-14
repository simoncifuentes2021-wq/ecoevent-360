import type { UserRole } from "@/types/roles";

export type OrderStatus =
  | "DRAFT"
  | "REQUESTED"
  | "APPROVED"
  | "PREPARING"
  | "LOADED"
  | "IN_TRANSIT"
  | "DELIVERED"
  | "RETURN_IN_PROGRESS"
  | "RETURNED"
  | "CLOSED"
  | "CANCELLED";

export type OrderItemStageStatus = "PENDING" | "COMPLETED" | "OBSERVED";
export type OrderEvidenceStage = "LOAD" | "DELIVERY" | "RETURN";

export type CatalogItem = {
  id: string;
  name: string;
  category?: string | null;
  description?: string | null;
  unit?: string | null;
  default_unit_price?: string | number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type CatalogItemCreate = {
  name: string;
  category?: string | null;
  description?: string | null;
  unit?: string | null;
  default_unit_price?: number | null;
  is_active?: boolean;
};

export type OrderProgress = {
  total_items: number;
  loaded_items: number;
  delivered_items: number;
  returned_items: number;
  load_progress_percentage: number;
  delivery_progress_percentage: number;
  return_progress_percentage: number;
};

export type OrderUser = {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
};

export type EventOrder = {
  id: string;
  event_id: string;
  requested_by?: string | null;
  assigned_to?: string | null;
  title: string;
  description?: string | null;
  status: OrderStatus;
  requested_date?: string | null;
  required_date?: string | null;
  total_amount?: string | number | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  closed_at?: string | null;
  event?: { id: string; name: string; client_id: string; client?: { id: string; business_name: string } | null } | null;
  assignee?: OrderUser | null;
  progress: OrderProgress;
  items?: EventOrderItem[];
};

export type EventOrderCreate = {
  title: string;
  description?: string | null;
  assigned_to?: string | null;
  requested_date?: string | null;
  required_date?: string | null;
  notes?: string | null;
};

export type EventOrderUpdate = Partial<EventOrderCreate>;

export type EventOrderItem = {
  id: string;
  order_id: string;
  catalog_item_id?: string | null;
  zone_id?: string | null;
  item_name_snapshot: string;
  quantity: string | number;
  unit?: string | null;
  unit_price?: string | number | null;
  total_price?: string | number | null;
  notes?: string | null;
  load_status: OrderItemStageStatus;
  delivery_status: OrderItemStageStatus;
  return_status: OrderItemStageStatus;
  loaded_at?: string | null;
  delivered_at?: string | null;
  returned_at?: string | null;
  loaded_by?: string | null;
  delivered_by?: string | null;
  returned_by?: string | null;
  load_observation?: string | null;
  delivery_observation?: string | null;
  return_observation?: string | null;
  created_at: string;
  updated_at: string;
};

export type EventOrderItemCreate = {
  catalog_item_id?: string | null;
  zone_id?: string | null;
  item_name_snapshot?: string | null;
  quantity: number;
  unit?: string | null;
  unit_price?: number | null;
  notes?: string | null;
};

export type EventOrderItemUpdate = Partial<EventOrderItemCreate>;

export type OrderEvidence = {
  id: string;
  event_id: string;
  order_id: string;
  order_item_id?: string | null;
  uploaded_by?: string | null;
  stage: OrderEvidenceStage;
  file_url: string;
  file_type?: string | null;
  file_name?: string | null;
  file_size?: number | null;
  description?: string | null;
  visible_to_client: boolean;
  created_at: string;
};
