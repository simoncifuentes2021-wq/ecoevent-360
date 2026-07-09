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
  status: string;
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
  status?: string;
};

export type EventSessionUpdate = Partial<EventSessionCreate>;
