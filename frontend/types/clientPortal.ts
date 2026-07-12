export type ClientPortalSectionKey =
  | "summary"
  | "services"
  | "operation"
  | "incidents"
  | "evidences"
  | "waste"
  | "carbon"
  | "forms"
  | "bike_zone"
  | "reports"
  | "recommendations";

export type ClientPortalWidgetKey =
  | "event_status"
  | "task_completion_rate"
  | "open_incidents"
  | "resolved_incidents"
  | "evidence_gallery"
  | "total_waste_kg"
  | "recycling_rate"
  | "carbon_total_tco2e"
  | "carbon_per_attendee"
  | "forms_total_responses"
  | "forms_transport_modes"
  | "forms_average_rating"
  | "bike_zone_total_registrations"
  | "reports_download";

export type ClientPortalSection = {
  id?: string | null;
  section_key: ClientPortalSectionKey;
  label: string;
  is_enabled: boolean;
  sort_order: number;
};

export type ClientPortalWidget = {
  id?: string | null;
  widget_key: ClientPortalWidgetKey;
  section_key: ClientPortalSectionKey;
  label: string;
  is_enabled: boolean;
  sort_order: number;
  visibility_config: Record<string, unknown>;
};

export type ClientPortalConfig = {
  id: string;
  client_id: string;
  event_id: string;
  scope: string;
  is_active: boolean;
  created_by?: string | null;
  created_at: string;
  updated_at: string;
  sections: ClientPortalSection[];
  widgets: ClientPortalWidget[];
};

export type ClientPortalConfigUpdate = {
  scope: string;
  is_active: boolean;
  sections: Omit<ClientPortalSection, "id">[];
  widgets: Omit<ClientPortalWidget, "id">[];
};

export type ClientPortalVisibleSection = {
  section_key: ClientPortalSectionKey;
  label: string;
  sort_order: number;
};

export type ClientPortalVisibleWidget = {
  widget_key: ClientPortalWidgetKey;
  section_key: ClientPortalSectionKey;
  label: string;
  sort_order: number;
  value?: string | number | boolean | null;
  data?: Record<string, unknown> | unknown[] | null;
  visibility_config: Record<string, unknown>;
};

export type ClientPortal = {
  event_id: string;
  client_id: string;
  config_id: string;
  sections: ClientPortalVisibleSection[];
  widgets: ClientPortalVisibleWidget[];
  data: Record<string, unknown>;
};
