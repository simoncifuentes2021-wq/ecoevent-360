import { api } from "@/lib/api";
import type { ListResponse } from "@/types/common";
import type { QrCode, QrCodeCreate } from "@/types/qr";

function listFrom<T>(raw: T[] | ListResponse<T> | { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number }): ListResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, limit: raw.length };
  const value = raw as { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number };
  const items = value.items ?? value.data ?? [];
  return { items, total: value.total ?? items.length, page: value.page ?? 1, limit: value.limit ?? items.length };
}

export async function getSurveyQrCodes(surveyId: string) {
  const raw = await api.get<QrCode[] | ListResponse<QrCode>>(`/surveys/${surveyId}/qr`);
  return listFrom(raw);
}

export function createSurveyQrCode(surveyId: string, data: QrCodeCreate) {
  return api.post<QrCode>(`/surveys/${surveyId}/qr`, data);
}

export function downloadQrCode(qrId: string) {
  return api.get<{ url?: string; file_url?: string }>(`/qr/${qrId}/download`);
}
