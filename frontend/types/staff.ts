import type { User } from "@/types/user";

export type EventStaff = {
  id?: string;
  event_id: string;
  user_id: string;
  user?: Pick<User, "id" | "full_name" | "email" | "role"> | null;
  role_in_event?: string | null;
  shift_start?: string | null;
  shift_end?: string | null;
  calendar_invitation_status?: "PENDING" | "SENT" | "ERROR" | "CANCELLED";
  calendar_invitation_error?: string | null;
  calendar_invitation_sent_at?: string | null;
  created_at?: string;
  session_id?: string | null;
  session_name?: string | null;
  show_assignment_id?: string | null;
};

export type EventStaffCreate = {
  user_id: string;
  role_in_event?: string | null;
  shift_start?: string | null;
  shift_end?: string | null;
};
