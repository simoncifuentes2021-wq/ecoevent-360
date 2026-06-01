import type { Zone } from "@/types/zone";

export type SurveyStatus = "DRAFT" | "ACTIVE" | "CLOSED" | "ARCHIVED";

export type Survey = {
  id: string;
  event_id: string;
  title: string;
  description?: string | null;
  google_form_url?: string | null;
  google_sheet_url?: string | null;
  status: SurveyStatus;
  opens_at?: string | null;
  closes_at?: string | null;
  created_at?: string;
  updated_at?: string;
  responses_count?: number;
};

export type SurveyCreate = {
  title: string;
  description?: string | null;
  google_form_url?: string | null;
  google_sheet_url?: string | null;
  status?: SurveyStatus;
  opens_at?: string | null;
  closes_at?: string | null;
};

export type SurveyUpdate = Partial<SurveyCreate>;

export type SurveyResponse = {
  id: string;
  survey_id: string;
  event_id?: string;
  zone_id?: string | null;
  zone?: Zone | null;
  response_external_id?: string | null;
  response_date?: string | null;
  age_range?: string | null;
  origin_commune?: string | null;
  transport_mode?: string | null;
  cleanliness_rating?: number | string | null;
  bathroom_rating?: number | string | null;
  recycling_visibility?: boolean | string | null;
  separated_waste?: boolean | string | null;
  general_rating?: number | string | null;
  would_recommend?: boolean | string | null;
  main_problem?: string | null;
  comments?: string | null;
  raw_data?: Record<string, unknown> | null;
  created_at?: string;
};

export type SurveySummary = {
  total_responses: number;
  average_rating: number;
  recommendation_rate: number;
  cleaning_positive_rate: number;
  bathroom_positive_rate: number;
  saw_recycling_points_rate: number;
  recycling_action_rate: number;
  main_problems: Array<{ name: string; value: number }>;
  transport_modes: Array<{ name: string; value: number }>;
  responses_by_zone: Array<{ name: string; value: number }>;
  rating_distribution: Array<{ name: string; value: number }>;
  comments_sample: string[];
};

export type CSVImportResult = {
  imported_rows?: number;
  skipped_rows?: number;
  duplicated_rows?: number;
  errors?: string[];
  message?: string;
};
