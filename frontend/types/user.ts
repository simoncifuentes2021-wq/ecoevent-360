import type { UserRole } from "@/types/roles";

export type User = {
  id: string;
  client_id: string | null;
  client?: { id: string; business_name: string } | null;
  full_name: string;
  email: string;
  phone: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type UserCreate = {
  full_name: string;
  email: string;
  phone?: string | null;
  password: string;
  role: UserRole;
  client_id?: string | null;
};

export type UserUpdate = {
  full_name?: string;
  phone?: string | null;
  password?: string;
  role?: UserRole;
  client_id?: string | null;
  is_active?: boolean;
};
