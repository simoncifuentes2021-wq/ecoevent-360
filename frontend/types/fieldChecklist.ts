export type FieldChecklistStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "BLOCKED";

export type FieldChecklistItem = {
  id: string;
  event_id: string;
  user_id: string;
  title: string;
  details: string | null;
  due_at: string;
  status: FieldChecklistStatus;
  status_note: string | null;
  reminder_sent_at: string | null;
  reminder_attempts: number;
  reminder_failed: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  owner_name: string;
  owner_email: string;
};

export type FieldChecklistPerson = { id: string; full_name: string; email: string };
export type FieldChecklistHistory = {
  id: string;
  actor_name: string;
  action: string;
  description: string;
  created_at: string;
};

export type FieldChecklistItemCreate = {
  user_id?: string;
  title: string;
  details?: string | null;
  due_at: string;
};

export type FieldChecklistItemUpdate = Partial<Pick<FieldChecklistItem, "title" | "details" | "due_at" | "status" | "status_note">>;
