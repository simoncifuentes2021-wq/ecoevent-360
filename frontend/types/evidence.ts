import type { User } from "@/types/user";

export type Evidence = {
  id: string;
  event_id: string;
  task_id?: string | null;
  incident_id?: string | null;
  uploaded_by?: string | null;
  uploader?: Pick<User, "id" | "full_name" | "email"> | null;
  file_url: string;
  file_type: string;
  filename?: string | null;
  description?: string | null;
  taken_at?: string | null;
  created_at?: string;
};
