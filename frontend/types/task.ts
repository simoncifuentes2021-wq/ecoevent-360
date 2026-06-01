import type { Event } from "@/types/event";
import type { User } from "@/types/user";
import type { Zone } from "@/types/zone";

export type TaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "OBSERVED" | "CANCELLED";
export type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type Task = {
  id: string;
  event_id: string;
  event?: Pick<Event, "id" | "name" | "start_date" | "status"> | null;
  zone_id?: string | null;
  zone?: Pick<Zone, "id" | "name"> | null;
  assigned_to?: string | null;
  assignee?: Pick<User, "id" | "full_name" | "email" | "role"> | null;
  assigned_user?: Pick<User, "id" | "full_name" | "email" | "role"> | null;
  title: string;
  description?: string | null;
  status: TaskStatus;
  priority: Priority;
  scheduled_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  observation?: string | null;
  created_by?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type TaskCreate = {
  title: string;
  description?: string | null;
  zone_id?: string | null;
  assigned_to?: string | null;
  priority: Priority;
  scheduled_at?: string | null;
};

export type TaskUpdate = Partial<TaskCreate> & {
  status?: TaskStatus;
};

export type TaskComplete = {
  observation?: string | null;
};
