export type EventFormType = "TRANSPORT_SURVEY" | "STAFF_TRANSPORT_SURVEY" | "BIKE_ZONE_REGISTRATION" | "EXPERIENCE_SURVEY" | "CUSTOM";
export type EventFormStatus = "DRAFT" | "ACTIVE" | "CLOSED" | "ARCHIVED";
export type FormFieldType = "TEXT" | "EMAIL" | "PHONE" | "NUMBER" | "TEXTAREA" | "SELECT" | "MULTI_SELECT" | "RADIO" | "CHECKBOX" | "DATE" | "RATING_1_5" | "RATING_1_7" | "YES_NO" | "FILE";

export type FormFieldOption = {
  id?: string;
  field_id?: string;
  label: string;
  value: string;
  sort_order: number;
};

export type FormField = {
  id: string;
  form_id: string;
  label: string;
  field_key: string;
  field_type: FormFieldType;
  help_text?: string | null;
  placeholder?: string | null;
  is_required: boolean;
  is_readonly?: boolean;
  sort_order: number;
  min_value?: number | string | null;
  max_value?: number | string | null;
  max_length?: number | null;
  analytics_key?: string | null;
  is_active?: boolean;
  options: FormFieldOption[];
};

export type EventForm = {
  id: string;
  event_id: string;
  session_id?: string | null;
  title: string;
  description?: string | null;
  form_type: EventFormType;
  public_slug: string;
  status: EventFormStatus;
  banner_url?: string | null;
  primary_logo_url?: string | null;
  secondary_logo_url?: string | null;
  primary_color: string;
  show_event_name: boolean;
  show_session_name: boolean;
  collect_personal_data: boolean;
  default_language: string;
  available_languages: string[];
  requires_language_selection: boolean;
  opens_at?: string | null;
  closes_at?: string | null;
  fields: FormField[];
};

export type EventFormCreate = {
  session_id?: string | null;
  title: string;
  description?: string | null;
  form_type: EventFormType;
  public_slug?: string | null;
  banner_url?: string | null;
  primary_logo_url?: string | null;
  secondary_logo_url?: string | null;
  primary_color?: string;
  show_event_name?: boolean;
  show_session_name?: boolean;
  collect_personal_data?: boolean;
  default_language?: string;
  available_languages?: string[];
  requires_language_selection?: boolean;
  generate_template?: boolean;
};

export type PublicFormOption = {
  label: string;
  value: string;
  sort_order: number;
};

export type PublicFormField = {
  label: string;
  field_key: string;
  field_type: FormFieldType;
  help_text?: string | null;
  placeholder?: string | null;
  is_required: boolean;
  is_readonly?: boolean;
  sort_order: number;
  min_value?: number | string | null;
  max_value?: number | string | null;
  max_length?: number | null;
  options: PublicFormOption[];
};

export type PublicEventForm = {
  title: string;
  description?: string | null;
  form_type: EventFormType;
  public_slug: string;
  banner_url?: string | null;
  primary_logo_url?: string | null;
  secondary_logo_url?: string | null;
  primary_color: string;
  show_event_name: boolean;
  show_session_name: boolean;
  default_language: string;
  available_languages: string[];
  requires_language_selection: boolean;
  event_name?: string | null;
  session_name?: string | null;
  venue_name?: string | null;
  language?: string | null;
  needs_language_selection: boolean;
  submit_label: string;
  fields: PublicFormField[];
};

export type FormResponseSubmit = {
  language: string;
  answers: Record<string, unknown>;
};

export type FormSubmitResult = {
  response_code?: string | null;
  bike_zone_code?: string | null;
  message: string;
};

export type EventFormSummary = {
  form_id: string;
  total_responses: number;
  responses_by_language: Array<{ name: string; value: number }>;
  transport_modes: Array<{ name: string; value: number }>;
  countries: Array<{ name: string; value: number }>;
  average_rating?: number | null;
  recommendation_rate?: number | null;
  bike_zone_total: number;
  bike_zone_checked_in: number;
  bike_zone_checked_out: number;
};

export type FormsSessionComparisonItem = {
  session_id: string;
  session_name: string;
  session_date?: string | null;
  start_time?: string | null;
  total_forms: number;
  active_forms: number;
  total_responses: number;
  transport_modes: Array<{ name: string; value: number }>;
  average_rating?: number | null;
  recommendation_rate?: number | null;
  main_problems: Array<{ name: string; value: number }>;
  bike_zone_total: number;
  bike_zone_checked_in: number;
  bike_zone_checked_out: number;
};

export type FormsSessionComparison = {
  event_id: string;
  sessions: FormsSessionComparisonItem[];
};

export type FormResponse = {
  id: string;
  form_id: string;
  event_id: string;
  session_id?: string | null;
  response_code?: string | null;
  respondent_name?: string | null;
  respondent_email?: string | null;
  respondent_phone?: string | null;
  language: string;
  raw_data: Record<string, unknown>;
  submitted_at: string;
};
