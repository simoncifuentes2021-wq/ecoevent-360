import type { Service } from "@/types/service";

export type EventService = {
  id: string;
  event_id: string;
  service_id: string;
  service?: Pick<Service, "id" | "name" | "category" | "unit" | "base_price"> | null;
  quantity: number;
  unit_price: number | string | null;
  total_price: number | string | null;
  notes?: string | null;
  created_at?: string;
};

export type EventServiceCreate = {
  service_id: string;
  quantity: number;
  unit_price?: number | null;
  notes?: string | null;
};

export type EventServiceUpdate = Partial<Omit<EventServiceCreate, "service_id">>;
