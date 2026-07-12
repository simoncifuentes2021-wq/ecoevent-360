import { api } from "@/lib/api";
import type { ClientPortal, ClientPortalConfig, ClientPortalConfigUpdate } from "@/types/clientPortal";

export function getClientPortalConfig(eventId: string) {
  return api.get<ClientPortalConfig>(`/events/${eventId}/client-portal-config`);
}

export function updateClientPortalConfig(eventId: string, data: ClientPortalConfigUpdate) {
  return api.put<ClientPortalConfig>(`/events/${eventId}/client-portal-config`, data);
}

export function applyClientPortalTemplate(eventId: string, templateKey: string) {
  return api.post<ClientPortalConfig>(`/events/${eventId}/client-portal-config/apply-template`, { template_key: templateKey });
}

export function getClientPortalPreview(eventId: string) {
  return api.get<ClientPortal>(`/events/${eventId}/client-portal-preview`);
}

export function getClientEventPortal(eventId: string) {
  return api.get<ClientPortal>(`/client/events/${eventId}/portal`);
}
