import { api } from "@/lib/api";
import type {
  FieldChecklistHistory,
  FieldChecklistItem,
  FieldChecklistItemCreate,
  FieldChecklistItemUpdate,
  FieldChecklistPerson,
} from "@/types/fieldChecklist";

export function getFieldChecklistPeople(eventId: string) {
  return api.get<FieldChecklistPerson[]>(`/events/${eventId}/field-checklists/people`);
}

export function getFieldChecklistEmailStatus() {
  return api.get<{ configured: boolean }>("/field-checklists/email-status");
}

export function getFieldChecklist(eventId: string, ownerId?: string) {
  const query = ownerId ? `?owner_id=${encodeURIComponent(ownerId)}` : "";
  return api.get<FieldChecklistItem[]>(`/events/${eventId}/field-checklists${query}`);
}

export function createFieldChecklistItem(eventId: string, data: FieldChecklistItemCreate) {
  return api.post<FieldChecklistItem>(`/events/${eventId}/field-checklists`, data);
}

export function updateFieldChecklistItem(itemId: string, data: FieldChecklistItemUpdate) {
  return api.patch<FieldChecklistItem>(`/field-checklists/${itemId}`, data);
}

export function getFieldChecklistHistory(itemId: string) {
  return api.get<FieldChecklistHistory[]>(`/field-checklists/${itemId}/history`);
}
