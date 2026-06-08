import type { ListResponse } from "@/types/common";

export type AuditLogStatus = "SUCCESS" | "FAILED" | "DENIED" | "INFO";
export type AuditLogModule =
  | "auth"
  | "users"
  | "clients"
  | "events"
  | "services"
  | "zones"
  | "staff"
  | "tasks"
  | "incidents"
  | "evidences"
  | "waste"
  | "carbon"
  | "operations"
  | "surveys"
  | "reports"
  | string;
export type AuditLogAction = string;

export type AuditLog = {
  id: string;
  user_id?: string | null;
  user_name?: string | null;
  user_email?: string | null;
  user_role?: string | null;
  event_id?: string | null;
  event_name?: string | null;
  client_id?: string | null;
  client_name?: string | null;
  task_id?: string | null;
  task_title?: string | null;
  incident_id?: string | null;
  incident_title?: string | null;
  zone_id?: string | null;
  zone_name?: string | null;
  action: string;
  module: string;
  entity_type?: string | null;
  entity_id?: string | null;
  status: string;
  old_data?: Record<string, unknown> | null;
  new_data?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  request_method?: string | null;
  request_path?: string | null;
  description?: string | null;
  created_at: string;
};

export type AuditLogFilters = {
  user_id?: string;
  event_id?: string;
  client_id?: string;
  task_id?: string;
  incident_id?: string;
  zone_id?: string;
  module?: string;
  action?: string;
  entity_type?: string;
  entity_id?: string;
  status?: string;
  from_date?: string;
  to_date?: string;
  q?: string;
  page?: number;
  limit?: number;
};

export type AuditLogListResponse = ListResponse<AuditLog> & {
  pages: number;
};

export type AuditLogSummary = {
  total: number;
  today: number;
  failedOrDenied: number;
  topModule: string;
  lastMovement: string;
};
