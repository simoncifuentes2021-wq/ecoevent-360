import type { IncidentStatus } from "@/types/incident";
import type { TaskStatus } from "@/types/task";
import type { User } from "@/types/user";

export type ShowStaffAssignment = {
  id: string;
  event_id: string;
  session_id: string;
  session_name?: string | null;
  event_staff_id: string;
  shift_start?: string | null;
  shift_end?: string | null;
  operational_role?: string | null;
  notes?: string | null;
  overlap_warning?: boolean;
  user?: Pick<User, "id" | "full_name" | "email" | "role"> | null;
  created_at: string;
  updated_at: string;
};

export type ShowStaffInput = {
  event_staff_id: string;
  shift_start?: string | null;
  shift_end?: string | null;
  operational_role?: string | null;
  notes?: string | null;
};

export type ShowOperationalSummary = {
  staff_count: number;
  active_shift_count: number;
  tasks_by_status: Partial<Record<TaskStatus, number>>;
  incidents_by_status: Partial<Record<IncidentStatus, number>>;
  evidence_count: number;
};
