import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { Client, ClientCreate, ClientEvent, ClientUpdate } from "@/types/client";
import type { ListResponse } from "@/types/common";

function normalizeList<T>(raw: T[] | ListResponse<T> | { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number }): ListResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, limit: raw.length || 20 };
  const value = raw as { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number };
  const items = value.items ?? value.data ?? [];
  const limit = value.limit ?? (items.length || 20);
  return {
    items,
    total: value.total ?? items.length,
    page: value.page ?? 1,
    limit
  };
}

export function getClients(params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<Client>>(`/clients${toQuery(params)}`);
}

export function getClient(id: string) {
  return api.get<Client>(`/clients/${id}`);
}

export function createClient(data: ClientCreate) {
  return api.post<Client>("/clients", data);
}

export function updateClient(id: string, data: ClientUpdate) {
  return api.patch<Client>(`/clients/${id}`, data);
}

export function deleteClient(id: string) {
  return api.delete<Client>(`/clients/${id}`);
}

export async function getClientEvents(id: string, params: Record<string, QueryValue> = {}) {
  const raw = await api.get<ClientEvent[] | ListResponse<ClientEvent> | { data?: ClientEvent[]; items?: ClientEvent[] }>(`/clients/${id}/events${toQuery(params)}`);
  return normalizeList(raw);
}
