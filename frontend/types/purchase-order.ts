export type PurchaseOrderStatus = "DRAFT" | "APPROVED" | "SENT" | "PARTIALLY_RECEIVED" | "RECEIVED" | "CANCELLED";

export type PurchaseOrderItem = {
  id: string;
  line_number: number;
  description: string;
  unit: string;
  quantity: number | string;
  received_quantity: number | string;
  unit_price: number | string;
  tax_rate: number | string;
  line_subtotal: number | string;
  line_tax: number | string;
  line_total: number | string;
};

export type PurchaseOrder = {
  id: string;
  order_number: string;
  version: number;
  status: PurchaseOrderStatus;
  event_id: string | null;
  event_name_snapshot: string | null;
  purpose: string;
  supplier_name: string;
  supplier_rut: string | null;
  supplier_email: string | null;
  supplier_phone: string | null;
  supplier_address: string | null;
  delivery_address: string | null;
  issue_date: string;
  required_date: string | null;
  payment_terms: string | null;
  notes: string | null;
  currency: "CLP" | "USD" | "EUR";
  subtotal: number | string;
  tax_total: number | string;
  total: number | string;
  created_by: string | null;
  approved_by: string | null;
  sent_by: string | null;
  approved_at: string | null;
  sent_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  items: PurchaseOrderItem[];
};

export type PurchaseOrderInput = Omit<PurchaseOrder, "id" | "order_number" | "version" | "status" | "event_name_snapshot" | "subtotal" | "tax_total" | "total" | "created_by" | "approved_by" | "sent_by" | "approved_at" | "sent_at" | "cancelled_at" | "cancellation_reason" | "created_at" | "updated_at" | "items"> & {
  items: Array<{ description: string; unit: string; quantity: number; unit_price: number; tax_rate: number }>;
};
