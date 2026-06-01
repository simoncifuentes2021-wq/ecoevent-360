import type { UserRole } from "@/types/roles";

export type AuthUser = {
  id: string;
  full_name: string;
  email: string;
  role: UserRole;
  client_id: string | null;
};

export type LoginRequest = {
  email: string;
  password: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
};
