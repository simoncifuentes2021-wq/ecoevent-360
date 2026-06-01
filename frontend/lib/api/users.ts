import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { User, UserCreate, UserUpdate } from "@/types/user";

export function getUsers(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<User>>(`/users${toQuery(params)}`);
}

export function getUser(id: string) {
  return api.get<User>(`/users/${id}`);
}

export function createUser(data: UserCreate) {
  return api.post<User>("/users", data);
}

export function updateUser(id: string, data: UserUpdate) {
  return api.patch<User>(`/users/${id}`, data);
}

export function deleteUser(id: string) {
  return api.delete<User>(`/users/${id}`);
}
