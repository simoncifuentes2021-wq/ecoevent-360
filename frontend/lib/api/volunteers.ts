import { api } from "@/lib/api";
import { API_URL } from "@/lib/constants";
import { getStoredToken } from "@/lib/auth";
import { toQuery } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { Event } from "@/types/event";
import type {
  MaterialContribution,
  PublicActivation,
  PublicVolunteerImpact,
  RecyclableMaterial,
  RecyclingActivation,
  VolunteerDashboard,
  VolunteerListItem,
  VolunteerResolve,
} from "@/types/volunteer";

export type ActivationInput = {
  event_id: string;
  session_id?: string | null;
  name: string;
  description?: string | null;
  location_name?: string | null;
  address?: string | null;
  starts_at: string;
  ends_at?: string | null;
  capacity?: number | null;
  allowed_material_ids: string[];
};

export type ContributionInput = {
  volunteer_id: string;
  items: Array<{ material_id: string; weight_kg: string }>;
  notes?: string | null;
  idempotency_key?: string;
};

export type VolunteerInput = {
  full_name: string;
  email: string;
  phone: string;
  organization?: string | null;
  consent_accepted: true;
  marketing_consent?: boolean;
};

export function getVolunteerEvents() {
  return api.get<ListResponse<Event>>("/events?page=1&limit=100");
}

export function getVolunteerActivations(eventId: string) {
  return api.get<RecyclingActivation[]>(`/events/${eventId}/recycling-activations`);
}

export function createVolunteerActivation(data: ActivationInput) {
  return api.post<RecyclingActivation>(`/events/${data.event_id}/recycling-activations`, data);
}

export function updateVolunteerActivation(id: string, data: Partial<ActivationInput> & { status?: RecyclingActivation["status"] }) {
  return api.patch<RecyclingActivation>(`/recycling-activations/${id}`, data);
}

export function getVolunteerMaterials(eventId: string) {
  return api.get<RecyclableMaterial[]>(`/events/${eventId}/waste-types`);
}

export function getVolunteerImpact(eventId: string, volunteerId: string) {
  return api.get<{
    full_name: string; total_weight_kg: string | number; activation_count: number;
    contribution_count: number; material_totals: Record<string, string | number>;
    contributions: PublicVolunteerImpact["contributions"];
    email: string; phone: string | null; unique_code: string;
    first_contribution_at: string | null; last_contribution_at: string | null;
  }>(`/events/${eventId}/volunteers/${volunteerId}/impact`);
}

export function updateVolunteer(eventId: string, volunteerId: string, data: Partial<Pick<VolunteerListItem, "full_name" | "email" | "phone" | "organization" | "status">>) {
  return api.patch(`/events/${eventId}/volunteers/${volunteerId}`, data);
}

export function getVolunteers(eventId: string, params: Record<string, string | number | undefined> = {}) {
  return api.get<ListResponse<VolunteerListItem>>(`/events/${eventId}/volunteers${toQuery(params)}`);
}

export function lookupVolunteer(activationId: string, query: string) {
  return api.get<VolunteerResolve | null>(`/recycling-activations/${activationId}/volunteers/lookup${toQuery({ q: query })}`);
}

export function createOrRegisterVolunteer(activationId: string, data: VolunteerInput) {
  return api.post<VolunteerResolve>(`/recycling-activations/${activationId}/volunteers`, data);
}

export function getVolunteerDashboard(eventId: string, params: Record<string, string | undefined> = {}) {
  return api.get<VolunteerDashboard>(`/events/${eventId}/recycling-dashboard${toQuery(params)}`);
}

export function getVolunteerContributions(eventId: string, params: Record<string, string | number | undefined> = {}) {
  return api.get<ListResponse<MaterialContribution>>(`/events/${eventId}/contributions${toQuery(params)}`);
}

export function createContribution(activationId: string, data: ContributionInput) {
  return api.post<MaterialContribution>(`/recycling-activations/${activationId}/contributions`, data);
}

export function updateContribution(id: string, data: Pick<ContributionInput, "items" | "notes">) {
  return api.put<MaterialContribution>(`/contributions/${id}`, data);
}

export function voidContribution(id: string, reason: string) {
  return api.post<MaterialContribution>(`/contributions/${id}/void`, { reason });
}

export function uploadContributionEvidence(id: string, file: File, description?: string) {
  const body = new FormData();
  body.append("file", file);
  if (description) body.append("description", description);
  return api.post<{ id: string; description: string | null; file_type: string; created_at: string }>(`/contributions/${id}/evidence`, body);
}

export function listContributionEvidence(id: string) {
  return api.get<Array<{ id: string; description: string | null; file_type: string | null; created_at: string }>>(`/contributions/${id}/evidence`);
}

export function getContributionEvidenceFile(contributionId: string, evidenceId: string) {
  return authenticatedBlob(`/contributions/${contributionId}/evidence/${evidenceId}/file`);
}

export function getPublicActivation(slug: string) {
  return api.get<PublicActivation>(`/public/volunteer-activations/${slug}`, { auth: false });
}

export function registerPublicVolunteer(slug: string, data: Omit<VolunteerInput, "consent_accepted">) {
  return api.post<{ activation_name: string; message: string }>(`/public/volunteer-activations/${slug}/register`, {
    ...data,
    consent_accepted: true,
    activation_slug: slug,
  }, { auth: false });
}

export function getPublicVolunteerImpact(token: string) {
  return api.get<PublicVolunteerImpact>(`/public/volunteer-impact/${token}`, { auth: false });
}

export function getPublicVolunteerEvidenceUrl(token: string, evidenceId: string) {
  return `${API_URL}/public/volunteer-impact/${encodeURIComponent(token)}/evidence/${encodeURIComponent(evidenceId)}/file`;
}

async function authenticatedBlob(path: string): Promise<Blob> {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) throw new Error("No se pudo descargar el archivo. Revisa tu conexión e inténtalo nuevamente.");
  return response.blob();
}

export function getActivationQr(activationId: string) {
  return authenticatedBlob(`/recycling-activations/${activationId}/qr.png`);
}

export function downloadVolunteerCsv(eventId: string, activationId?: string) {
  const suffix = toQuery({ activation_id: activationId });
  return authenticatedBlob(`/events/${eventId}/volunteer-contributions.csv${suffix}`);
}
