import { API_URL } from "@/lib/constants";
import { getStoredToken } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { GenerateReportResponse, Report } from "@/types/report";

function listFrom<T>(raw: T[] | ListResponse<T> | { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number }): ListResponse<T> {
  if (Array.isArray(raw)) return { items: raw, total: raw.length, page: 1, limit: raw.length };
  const value = raw as { data?: T[]; items?: T[]; total?: number; page?: number; limit?: number };
  const items = value.items ?? value.data ?? [];
  return { items, total: value.total ?? items.length, page: value.page ?? 1, limit: value.limit ?? items.length };
}

export async function getEventReports(eventId: string, params: Record<string, QueryValue> = {}) {
  const raw = await api.get<Report[] | ListResponse<Report>>(`/events/${eventId}/reports${toQuery(params)}`);
  return listFrom(raw);
}

export async function generateFinalReport(eventId: string, options: Record<string, unknown> = {}): Promise<GenerateReportResponse> {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}/events/${eventId}/reports/final`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(options)
  });

  if (!response.ok) {
    let detail = "No se pudo generar el reporte.";
    try {
      const data = await response.json() as { detail?: string };
      detail = data.detail || detail;
    } catch {}
    throw new ApiError(response.status, detail);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/pdf")) {
    const blob = await response.blob();
    return { blob, filename: filenameFromDisposition(response.headers.get("content-disposition")) };
  }
  return response.json() as Promise<GenerateReportResponse>;
}

export function getReport(reportId: string) {
  return api.get<Report>(`/reports/${reportId}`);
}

export async function downloadReport(reportId: string): Promise<GenerateReportResponse> {
  const token = getStoredToken();
  const response = await fetch(`${API_URL}/reports/${reportId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });

  if (!response.ok) {
    let detail = "No se pudo descargar el PDF.";
    try {
      const data = await response.json() as { detail?: string };
      detail = data.detail || detail;
    } catch {}
    throw new ApiError(response.status, detail);
  }

  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/pdf") || contentType.includes("application/octet-stream")) {
    return { blob: await response.blob(), filename: filenameFromDisposition(response.headers.get("content-disposition")) };
  }
  return response.json() as Promise<GenerateReportResponse>;
}

export function deleteReport(reportId: string) {
  return api.delete<void>(`/reports/${reportId}`);
}

export function markReportDelivered(reportId: string) {
  return api.patch<Report>(`/reports/${reportId}/deliver`, {});
}

function filenameFromDisposition(disposition: string | null) {
  const match = disposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1];
}
