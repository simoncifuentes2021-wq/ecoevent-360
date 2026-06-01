import type { Priority } from "@/types/task";
import type { Zone } from "@/types/zone";

export type AlertStatus = "OPEN" | "ACTIVE" | "RESOLVED" | "CLOSED" | "CANCELLED";

export type Alert = {
  id: string;
  event_id: string;
  zone_id?: string | null;
  zone?: Pick<Zone, "id" | "name"> | null;
  title: string;
  description?: string | null;
  alert_type?: string | null;
  type?: string | null;
  priority?: Priority | "URGENT" | null;
  status: AlertStatus;
  created_at?: string | null;
  resolved_at?: string | null;
};

export type AlertCreate = {
  zone_id?: string | null;
  title: string;
  description?: string | null;
  alert_type?: string | null;
  priority?: Priority | "URGENT";
};

export type AlertResolve = {
  resolution?: string | null;
};
