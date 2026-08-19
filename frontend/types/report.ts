import type { Event } from "@/types/event";
import type { User } from "@/types/user";

export type ReportStatus = "DRAFT" | "GENERATED" | "DELIVERED" | "ARCHIVED" | "FAILED";
export type ReportScope = "EVENT" | "SHOW";
export type ReportDataAvailability = "AVAILABLE" | "NO_DATA" | "EVENT_LEVEL_ONLY" | "NOT_APPLICABLE";
export type ReportSectionType = "COVER" | "EXECUTIVE_SUMMARY" | "EVENT_INFO" | "SHOW_INFO" | "SERVICES" | "OPERATIONS" | "STAFF" | "TASKS" | "INCIDENTS" | "FORMS" | "BIKE_ZONE" | "WASTE" | "CARBON" | "ENVIRONMENTAL_IMPACT" | "EVIDENCES" | "RECOMMENDATIONS" | "CONCLUSION" | "CUSTOM";
export type ReportLayoutVariant = "HERO_IMAGE_TEXT" | "KPI_GRID" | "TWO_COLUMN" | "METRIC_LIST" | "FEATURE_CHART" | "PHOTO_GRID" | "EDITORIAL" | "TEXT_IMAGE" | "BIG_NUMBERS";
export type ReportTemplateKey = "ENVIRONMENTAL_PREMIUM" | "ENVIRONMENTAL_STORY" | "BIKE_ZONE" | "OPERATIONS" | "EXECUTIVE" | "COMPLETE";
export type ReportPageOverrideMode = "AUTO" | "KEEP_WITH_NEXT" | "OWN_PAGE" | "GROUP_WITH" | "NEW_PAGE";
export type ReportEditorialConfig = { mode: "AUTO" | "CUSTOM"; cover_style: "FULL_PHOTO" | "SIDE_PHOTO" | "EDITORIAL" | "MINIMAL_PREMIUM"; cover_evidence_id?: string | null; featured_kpi_ids: string[]; page_overrides: Record<string, { mode: ReportPageOverrideMode; group_with?: string | null }>; chart_types: Record<string, "BAR" | "DONUT" | "COMPARISON" | "DISTRIBUTION"> };
export type ReportPagePlan = { mode: "AUTO" | "CUSTOM"; pages: Array<{ number: number; recipe: string; density: "LOW" | "MEDIUM" | "HIGH"; title: string; section_keys: string[] }> };
export type ReportTheme = { primary_color: string; secondary_color: string; accent_color: string; background_color: string; text_color: string; muted_color: string; cover_style: "DARK_OVERLAY" | "COLOR_BLOCK" | "MINIMAL"; header_style: "MINIMAL" | "BRANDED"; footer_style: "PAGE_NUMBER" | "EVENT_AND_PAGE" | "NONE"; show_page_numbers: boolean; show_event_name_in_footer: boolean };
export type ReportPublication = { id: string; report_id: string; revision_id?: string | null; publication_number: number; status: "GENERATED" | "DELIVERED" | "ARCHIVED"; sha256: string; file_size: number; page_count: number; generated_by?: string | null; generated_at: string; delivered_by?: string | null; delivered_at?: string | null; created_at: string };
export type ReportScalar = string | number | boolean | null;
export type ReportField = { key: string; label: string; auto_value: ReportScalar; value: ReportScalar; unit?: string | null; description?: string | null; is_overridden: boolean; source: string; is_visible?: boolean };
export type ReportSectionContent = { text?: string | null; show_traceability?: boolean; fields: ReportField[]; items: Array<Record<string, ReportScalar>> };
export type ReportSection = { id: string; report_id: string; section_key: string; section_type: ReportSectionType; title: string; layout_variant: ReportLayoutVariant; is_enabled: boolean; sort_order: number; content: ReportSectionContent; source_snapshot: ReportSectionContent; source_metadata: { availability: ReportDataAvailability; source_scope: string; generated_at?: string }; is_custom: boolean; edit_version: number; created_at: string; updated_at: string };
export type ReportEvidence = { id: string; report_id: string; section_id?: string | null; evidence_id: string; sort_order: number; caption?: string | null; is_enabled: boolean; created_at: string };
export type ReportRevision = { id: string; report_id: string; revision_number: number; snapshot: Record<string, unknown>; created_by?: string | null; note?: string | null; created_at: string };
export type AvailableReportEvidence = { id: string; file_type?: string | null; description?: string | null; taken_at?: string | null; session_id?: string | null; preview_url: string; selected: boolean };

export type Report = {
  id: string;
  event_id: string;
  event?: Event | null;
  title: string;
  summary?: string | null;
  pdf_url?: string | null;
  file_url?: string | null;
  status: ReportStatus | string;
  scope?: ReportScope;
  session_id?: string | null;
  created_by?: string | null;
  edit_version?: number;
  updated_at?: string | null;
  template_key?: ReportTemplateKey;
  theme?: Partial<ReportTheme>;
  editorial_config?: Partial<ReportEditorialConfig>;
  generated_by?: string | null;
  generator?: Pick<User, "id" | "full_name" | "email"> | null;
  generated_at?: string | null;
  delivered_at?: string | null;
  created_at?: string | null;
  sections?: string[] | Array<{ key?: string; label?: string; included?: boolean }> | null;
  metadata?: Record<string, unknown> | null;
};

export type ReportEditor = Report & { scope: ReportScope; edit_version: number; sections: ReportSection[]; evidences: ReportEvidence[] };

export type GenerateReportResponse = {
  id?: string;
  report_id?: string;
  title?: string;
  pdf_url?: string;
  file_url?: string;
  status?: ReportStatus | string;
  message?: string;
  blob?: Blob;
  filename?: string;
};

export type ReportSectionStatus = {
  key: string;
  label: string;
  status: "complete" | "empty" | "partial";
  count?: number;
  description: string;
};

export type ReportPreview = {
  event?: Event;
  services_count: number;
  tasks_total: number;
  tasks_completed: number;
  incidents_total: number;
  incidents_resolved: number;
  evidences_count: number;
  waste_total_kg: number;
  waste_recovery_rate: number;
  carbon_total_tco2e: number;
  carbon_kgco2e_per_attendee: number;
  survey_total_responses: number;
  survey_average_rating: number;
};
