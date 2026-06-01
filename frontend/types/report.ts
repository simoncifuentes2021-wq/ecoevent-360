import type { Event } from "@/types/event";
import type { User } from "@/types/user";

export type ReportStatus = "DRAFT" | "GENERATED" | "DELIVERED" | "ARCHIVED" | "FAILED";

export type Report = {
  id: string;
  event_id: string;
  event?: Event | null;
  title: string;
  summary?: string | null;
  pdf_url?: string | null;
  file_url?: string | null;
  status: ReportStatus | string;
  generated_by?: string | null;
  generator?: Pick<User, "id" | "full_name" | "email"> | null;
  generated_at?: string | null;
  delivered_at?: string | null;
  created_at?: string | null;
  sections?: string[] | Array<{ key?: string; label?: string; included?: boolean }> | null;
  metadata?: Record<string, unknown> | null;
};

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
