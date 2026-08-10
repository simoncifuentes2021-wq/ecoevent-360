import { API_URL } from "@/lib/constants";
import { clearSession, getStoredToken } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import { toQuery, type QueryValue } from "@/lib/api/query";
import type { ListResponse } from "@/types/common";
import type { AvailableReportEvidence, GenerateReportResponse, Report, ReportEditor, ReportPagePlan, ReportPublication, ReportRevision, ReportScope, ReportSection, ReportTemplateKey, ReportTheme, ReportEditorialConfig } from "@/types/report";

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

  handleUnauthorized(response);

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

  handleUnauthorized(response);

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

export function createReportDraft(eventId: string, scope: ReportScope, sessionId?: string) {
  return api.post<ReportEditor>(`/events/${eventId}/reports/drafts`, { scope, session_id: sessionId || null });
}
export function getReportEditor(reportId: string) { return api.get<ReportEditor>(`/reports/${reportId}/editor`); }
export function updateReportDesign(reportId: string, editVersion: number, templateKey: ReportTemplateKey, theme: ReportTheme, editorialConfig?: ReportEditorialConfig) { return api.patch<ReportEditor>(`/reports/${reportId}`, { edit_version: editVersion, template_key: templateKey, theme, editorial_config: editorialConfig }); }
export function updateReportEditorialConfig(reportId: string, editVersion: number, editorialConfig: ReportEditorialConfig) { return api.patch<ReportEditor>(`/reports/${reportId}`, { edit_version: editVersion, editorial_config: editorialConfig }); }
export function getReportPagePlan(reportId: string) { return api.get<ReportPagePlan>(`/reports/${reportId}/page-plan`); }
export async function getReportHtmlPreview(reportId: string) { const token = getStoredToken(); const response = await fetch(`${API_URL}/reports/${reportId}/html-preview`, { headers: token ? { Authorization: `Bearer ${token}` } : {}, cache: "no-store" }); handleUnauthorized(response); if (!response.ok) throw new ApiError(response.status, "No se pudo actualizar la vista previa."); return response.text(); }
export function updateReportSection(reportId: string, sectionId: string, body: { title?: string; is_enabled?: boolean; layout_variant?: ReportSection["layout_variant"]; content?: ReportSection["content"]; edit_version: number }) { return api.patch<ReportSection>(`/reports/${reportId}/sections/${sectionId}`, body); }
export function reorderReportSections(reportId: string, sectionIds: string[], editVersion: number) { return api.put<ReportEditor>(`/reports/${reportId}/sections/order`, { section_ids: sectionIds, edit_version: editVersion }); }
export function deleteCustomReportSection(reportId: string, sectionId: string, editVersion: number) { return api.delete<void>(`/reports/${reportId}/sections/${sectionId}?edit_version=${editVersion}`); }
export function refreshReport(reportId: string, editVersion: number) { return api.post<ReportEditor>(`/reports/${reportId}/refresh?edit_version=${editVersion}`, {}); }
export function resetReportField(reportId: string, sectionId: string, fieldKey: string, editVersion: number) { return api.post<ReportSection>(`/reports/${reportId}/sections/${sectionId}/fields/${fieldKey}/reset?edit_version=${editVersion}`, {}); }
export function addCustomReportSection(reportId: string, title: string, text: string, editVersion: number) { return api.post<ReportSection>(`/reports/${reportId}/sections`, { title, content: { kind: "TEXT", text }, edit_version: editVersion }); }
export function getAvailableReportEvidences(reportId: string) { return api.get<AvailableReportEvidence[]>(`/reports/${reportId}/available-evidences`); }
export function addReportEvidence(reportId: string, evidenceId: string, editVersion: number, sectionId?: string, caption?: string) { return api.post(`/reports/${reportId}/evidences`, { evidence_id: evidenceId, section_id: sectionId || null, caption: caption || null, edit_version: editVersion }); }
export function removeReportEvidence(reportId: string, itemId: string, editVersion: number) { return api.delete(`/reports/${reportId}/evidences/${itemId}?edit_version=${editVersion}`); }
export function updateReportEvidence(reportId: string, itemId: string, editVersion: number, sectionId?: string | null, caption?: string | null, isEnabled = true) { return api.patch(`/reports/${reportId}/evidences/${itemId}`, { section_id: sectionId || null, caption: caption || null, is_enabled: isEnabled, edit_version: editVersion }); }
export function getReportRevisions(reportId: string) { return api.get<ReportRevision[]>(`/reports/${reportId}/revisions`); }
export function createReportRevision(reportId: string, note: string, editVersion: number) { return api.post<ReportRevision>(`/reports/${reportId}/revisions`, { note: note || null, edit_version: editVersion }); }
export function restoreReportRevision(reportId: string, revisionId: string, editVersion: number) { return api.post<ReportEditor>(`/reports/${reportId}/revisions/${revisionId}/restore`, { edit_version: editVersion }); }
export function getReportPublications(reportId: string) { return api.get<ReportPublication[]>(`/reports/${reportId}/publications`); }
export function generateReportPublication(reportId: string, idempotencyKey: string) { return api.post<ReportPublication>(`/reports/${reportId}/publications`, { idempotency_key: idempotencyKey }); }
export function deliverReportPublication(publicationId: string) { return api.post<ReportPublication>(`/reports/publications/${publicationId}/deliver`, {}); }
async function authenticatedPdf(path: string) { const token = getStoredToken(); const response = await fetch(`${API_URL}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} }); handleUnauthorized(response); if (!response.ok) throw new ApiError(response.status, "No se pudo obtener el PDF."); return response.blob(); }
export function previewReportPdf(reportId: string) { return authenticatedPdf(`/reports/${reportId}/pdf-preview`); }
export function downloadReportPublication(publicationId: string, inline = false) { return authenticatedPdf(`/reports/publications/${publicationId}/download?inline=${inline}`); }

function filenameFromDisposition(disposition: string | null) {
  const match = disposition?.match(/filename="?([^"]+)"?/i);
  return match?.[1];
}

function handleUnauthorized(response: Response) {
  if (response.status === 401) {
    clearSession();
    if (typeof window !== "undefined") window.location.href = "/login";
  }
}
