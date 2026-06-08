export type EventStatus =
  | "QUOTE"
  | "PLANNING"
  | "IN_PROGRESS"
  | "FINISHED"
  | "REPORT_DELIVERED"
  | "CANCELLED";

export type Event = {
  id: string;
  client_id: string;
  client?: { id: string; business_name: string; rut?: string | null; contact_email?: string | null };
  name: string;
  event_type: string | null;
  description?: string | null;
  location_name?: string | null;
  address?: string | null;
  city?: string | null;
  region?: string | null;
  country?: string | null;
  latitude?: string | number | null;
  longitude?: string | number | null;
  start_date: string;
  end_date: string;
  estimated_attendees: number | null;
  real_attendees: number | null;
  status: EventStatus;
  hidden_from_operations: boolean;
  created_at: string;
  updated_at: string;
};

export type EventCreate = {
  client_id: string;
  name: string;
  event_type?: string | null;
  description?: string | null;
  location_name?: string | null;
  address?: string | null;
  city?: string | null;
  region?: string | null;
  country?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  start_date: string;
  end_date: string;
  estimated_attendees?: number | null;
  real_attendees?: number | null;
  status?: EventStatus;
  hidden_from_operations?: boolean;
};

export type EventUpdate = Partial<EventCreate>;
