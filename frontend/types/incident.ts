import type { Priority } from "@/types/task";
import type { User } from "@/types/user";
import type { Zone } from "@/types/zone";

export type IncidentStatus = "REPORTED" | "ASSIGNED" | "IN_PROGRESS" | "RESOLVED" | "CLOSED" | "CANCELLED";
export type IncidentType = "SANITARY" | "WASTE" | "CLEANING" | "ENVIRONMENTAL" | "SAFETY" | "OTHER";

export type Incident = {
  id: string;
  event_id: string;
  session_id?: string | null;
  session_name?: string | null;
  source_task_id?: string | null;
  zone_id?: string | null;
  zone?: Pick<Zone, "id" | "name"> | null;
  reported_by?: string | null;
  reporter?: Pick<User, "id" | "full_name" | "email"> | null;
  assigned_to?: string | null;
  assignee?: Pick<User, "id" | "full_name" | "email"> | null;
  title: string;
  description: string;
  incident_type?: IncidentType | null;
  type?: IncidentType | null;
  status: IncidentStatus;
  priority: Priority;
  source?: string | null;
  solution?: string | null;
  created_at?: string;
  resolved_at?: string | null;
  closed_at?: string | null;
};

export type IncidentCreate = {
  session_id?: string | null;
  source_task_id?: string | null;
  zone_id?: string | null;
  title: string;
  description: string;
  incident_type: IncidentType;
  priority: Priority;
  assigned_to?: string | null;
};

export type IncidentUpdate = Partial<IncidentCreate> & {
  status?: IncidentStatus;
  reassignment_reason?: string | null;
};

export type IncidentResolve = {
  solution: string;
  evidence_id?: string | null;
};
