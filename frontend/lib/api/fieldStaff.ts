import { API_URL } from "@/lib/constants";
import { getStoredToken } from "@/lib/auth";
import type { RecyclingActivation } from "@/types/volunteer";

export type FieldStaff = { id: string; event_id: string; full_name: string; rut: string; active: boolean; must_change_password: boolean; activation_ids: string[]; activation_names: string[]; created_at: string };
export type FieldStaffCreateResult = { staff: FieldStaff; temporary_password: string };

async function call<T>(path: string, init: RequestInit = {}, fieldToken?: string): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const adminToken = getStoredToken();
  if (fieldToken) headers.set("X-Field-Staff-Token", fieldToken);
  else if (adminToken) headers.set("Authorization", `Bearer ${adminToken}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) throw new Error(typeof body?.detail === "string" ? body.detail : "No se pudo completar la solicitud.");
  return body as T;
}

export const fieldStaffApi = {
  list: (eventId: string) => call<FieldStaff[]>(`/events/${eventId}/field-staff`),
  portalStatus: (eventId: string) => call<{ event_id: string; enabled: boolean }>(`/events/${eventId}/field-staff-portal`),
  updatePortalStatus: (eventId: string, enabled: boolean) => call<{ event_id: string; enabled: boolean }>(`/events/${eventId}/field-staff-portal`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  create: (eventId: string, value: { full_name: string; rut: string; activation_ids: string[] }) => call<FieldStaffCreateResult>(`/events/${eventId}/field-staff`, { method: "POST", body: JSON.stringify(value) }),
  update: (id: string, value: Partial<Pick<FieldStaff, "full_name" | "active">> & { activation_ids?: string[] }) => call<FieldStaff>(`/field-staff/${id}`, { method: "PATCH", body: JSON.stringify(value) }),
  reset: (id: string) => call<{ temporary_password: string }>(`/field-staff/${id}/reset-password`, { method: "POST" }),
  login: (eventId: string, rut: string, password: string) => call<{ access_token: string; staff: FieldStaff; event_name: string }>("/public/field-staff/login", { method: "POST", body: JSON.stringify({ event_id: eventId, rut, password }) }),
  activations: (token: string) => call<RecyclingActivation[]>("/field-staff/me/activations", {}, token),
  changePassword: (token: string, new_password: string) => call<void>("/field-staff/me/password", { method: "POST", body: JSON.stringify({ new_password }) }, token),
  searchVolunteers: (token: string, q: string) => call<Array<{ id: string; full_name: string; unique_code: string; total_weight_kg_in_event: number; activation_names: string[] }>>(`/field-staff/me/volunteers?q=${encodeURIComponent(q)}`, {}, token),
  history: (token: string, id: string) => call<any>(`/field-staff/me/volunteers/${id}/history`, {}, token),
  registerVolunteer: (token: string, activationId: string, value: Record<string, unknown>) => call<any>(`/field-staff/me/activations/${activationId}/volunteers`, { method: "POST", body: JSON.stringify(value) }, token),
  contribute: (token: string, activationId: string, value: Record<string, unknown>, photo: File) => {
    const body = new FormData();
    body.append("payload", JSON.stringify(value));
    body.append("file", photo);
    body.append("description", "Foto de evidencia del aporte");
    return call<any>(`/field-staff/me/activations/${activationId}/contributions`, { method: "POST", body }, token);
  },
};
