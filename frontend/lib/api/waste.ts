import { api } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { EventWastePublicForm, PublicCollectionPoint, PublicWasteSubmission, WasteCollectionPoint, WasteCollectionRecord, WasteCollectionSummary, WasteRecord, WasteRecordCreate, WasteRecordUpdate } from "@/types/waste";

function normalize(value: WasteRecord[] | ListResponse<WasteRecord>): ListResponse<WasteRecord> {
  if (Array.isArray(value)) return { items: value, total: value.length, page: 1, limit: value.length || 20 };
  return value;
}

export function getWasteSummary(eventId: string) {
  return api.get<unknown>(`/events/${eventId}/waste-summary`);
}

export async function getWasteRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return normalize(await api.get<WasteRecord[] | ListResponse<WasteRecord>>(`/events/${eventId}/waste-records${toQuery(params)}`));
}

export function createWasteRecord(eventId: string, data: WasteRecordCreate) {
  return api.post<WasteRecord>(`/events/${eventId}/waste-records`, data);
}

export function updateWasteRecord(recordId: string, data: WasteRecordUpdate) {
  return api.patch<WasteRecord>(`/waste-records/${recordId}`, data);
}

export function deleteWasteRecord(recordId: string) {
  return api.delete<WasteRecord>(`/waste-records/${recordId}`);
}

export function getCollectionPoints(eventId: string) {
  return api.get<WasteCollectionPoint[]>(`/events/${eventId}/waste-collection-points`);
}

export function createCollectionPoint(eventId: string, data: Partial<WasteCollectionPoint>) {
  return api.post<WasteCollectionPoint>(`/events/${eventId}/waste-collection-points`, data);
}

export function updateCollectionPoint(pointId: string, data: Partial<WasteCollectionPoint>) {
  return api.patch<WasteCollectionPoint>(`/waste-collection-points/${pointId}`, data);
}

export function getEventWastePublicForm(eventId: string) {
  return api.get<EventWastePublicForm>(`/events/${eventId}/waste-public-form`);
}

export function updateEventWastePublicForm(eventId: string, action: "activate" | "close" | "regenerate-token") {
  return api.patch<EventWastePublicForm>(`/events/${eventId}/waste-public-form/${action}`, {});
}

export function getWasteCollectionSummary(eventId: string) {
  return api.get<WasteCollectionSummary>(`/events/${eventId}/waste-collection-summary`);
}

export function getWasteCollectionRecords(eventId: string, params: Record<string, QueryValue> = {}) {
  return api.get<ListResponse<WasteCollectionRecord>>(`/events/${eventId}/waste-collection-records${toQuery(params)}`);
}

export function getPublicCollectionPoint(token: string) {
  return api.get<PublicCollectionPoint>(`/public/waste-forms/${encodeURIComponent(token)}`, { auth: false });
}

export function submitPublicWaste(token: string, item: PublicWasteSubmission) {
  return submitPublicWasteBatch(token, [item]);
}

export function submitPublicWasteBatch(token: string, items: PublicWasteSubmission[]) {
  return api.post<{ synced: { client_generated_id: string; synced_at: string }[]; rejected: { client_generated_id: string; reason: string }[] }>(
    `/public/waste-forms/${encodeURIComponent(token)}/records`, { items }, { auth: false }
  );
}
