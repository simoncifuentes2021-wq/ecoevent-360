import type { Event } from "@/types/event";

export type Client = {
  id: string;
  business_name: string;
  rut: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  address: string | null;
  industry: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type ClientCreate = {
  business_name: string;
  rut?: string | null;
  contact_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  address?: string | null;
  industry?: string | null;
  notes?: string | null;
};

export type ClientUpdate = Partial<ClientCreate> & {
  is_active?: boolean;
};

export type ClientEvent = Pick<
  Event,
  "id" | "name" | "event_type" | "start_date" | "end_date" | "status" | "estimated_attendees"
>;
