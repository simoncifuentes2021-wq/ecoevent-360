export type EventSessionStatus = "PLANNED" | "READY" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type EventSession = {
  id: string;
  event_id: string;
  name: string;
  description?: string | null;
  session_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  venue_name?: string | null;
  stage_name?: string | null;
  expected_attendees: number;
  real_attendees?: number | null;
  responsible_id?: string | null;
  status: EventSessionStatus;
  sort_order: number;
  internal_notes?: string | null;
  archived_at?: string | null;
  overlap_warning?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type EventSessionCreate = {
  name: string;
  description?: string | null;
  session_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  venue_name?: string | null;
  stage_name?: string | null;
  expected_attendees?: number;
  real_attendees?: number | null;
  responsible_id?: string | null;
  status?: EventSessionStatus;
  sort_order?: number;
  internal_notes?: string | null;
};

export type EventSessionUpdate = Partial<EventSessionCreate>;
