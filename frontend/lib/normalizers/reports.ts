import { buildEventDashboardFromFallbackData, normalizeEventDashboard } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";
import type { Report, GenerateReportResponse, ReportPreview, ReportSectionStatus } from "@/types/report";

export function normalizeReport(raw: unknown): Report {
  const data = raw && typeof raw === "object" ? raw as Partial<Report> : {};
  return {
    id: String(data.id ?? ""),
    event_id: String(data.event_id ?? data.event?.id ?? ""),
    event: data.event ?? null,
    title: data.title ?? "Reporte final del evento",
    summary: data.summary ?? null,
    pdf_url: data.pdf_url ?? data.file_url ?? null,
    file_url: data.file_url ?? null,
    status: data.status ?? "GENERATED",
    generated_by: data.generated_by ?? null,
    generator: data.generator ?? null,
    generated_at: data.generated_at ?? data.created_at ?? null,
    delivered_at: data.delivered_at ?? null,
    created_at: data.created_at ?? null,
    sections: data.sections ?? null,
    metadata: data.metadata ?? null
  };
}

export function normalizeReports(raw: unknown): Report[] {
  if (Array.isArray(raw)) return raw.map(normalizeReport);
  if (raw && typeof raw === "object") {
    const data = raw as { items?: unknown[]; data?: unknown[] };
    return (data.items ?? data.data ?? []).map(normalizeReport);
  }
  return [];
}

export function normalizeGenerateReportResponse(raw: unknown): GenerateReportResponse {
  if (raw instanceof Blob) return { blob: raw };
  const data = raw && typeof raw === "object" ? raw as GenerateReportResponse : {};
  return data;
}

export function normalizeReportPreview(raw: unknown): ReportPreview {
  const dashboard = normalizeEventDashboard(raw);
  return previewFromDashboard(dashboard);
}

export function previewFromDashboard(dashboard: EventDashboard): ReportPreview {
  return {
    event: dashboard.event,
    services_count: 0,
    tasks_total: dashboard.tasks.total,
    tasks_completed: dashboard.tasks.completed,
    incidents_total: dashboard.incidents.total,
    incidents_resolved: dashboard.incidents.resolved,
    evidences_count: dashboard.evidences.total,
    waste_total_kg: dashboard.waste.total_kg,
    waste_recovery_rate: dashboard.waste.recovery_rate,
    carbon_total_tco2e: dashboard.carbon.total_tco2e,
    carbon_kgco2e_per_attendee: dashboard.carbon.kgco2e_per_attendee,
    survey_total_responses: dashboard.survey.total_responses,
    survey_average_rating: dashboard.survey.average_rating
  };
}

export function buildReportSectionChecklist(preview: ReportPreview): ReportSectionStatus[] {
  return [
    { key: "event", label: "Datos generales", status: preview.event ? "complete" : "partial", description: preview.event ? "Evento identificado correctamente." : "Faltan datos generales." },
    { key: "services", label: "Servicios contratados", status: preview.services_count > 0 ? "complete" : "empty", count: preview.services_count, description: preview.services_count ? "Servicios disponibles para el informe." : "Sin servicios registrados." },
    { key: "tasks", label: "Tareas y cumplimiento", status: preview.tasks_total > 0 ? "complete" : "empty", count: preview.tasks_total, description: `${preview.tasks_completed} tareas completadas de ${preview.tasks_total}.` },
    { key: "incidents", label: "Incidencias", status: preview.incidents_total > 0 ? "complete" : "empty", count: preview.incidents_total, description: `${preview.incidents_resolved} incidencias resueltas.` },
    { key: "evidences", label: "Evidencias", status: preview.evidences_count > 0 ? "complete" : "empty", count: preview.evidences_count, description: preview.evidences_count ? "Hay respaldos disponibles." : "Sin evidencias registradas." },
    { key: "waste", label: "Gestion de residuos", status: preview.waste_total_kg > 0 ? "complete" : "empty", description: `${preview.waste_total_kg.toFixed(1)} kg registrados.` },
    { key: "carbon", label: "Huella de carbono", status: preview.carbon_total_tco2e > 0 ? "complete" : "empty", description: `${preview.carbon_total_tco2e.toFixed(2)} tCO2e estimadas.` },
    { key: "surveys", label: "Encuestas", status: preview.survey_total_responses > 0 ? "complete" : "empty", count: preview.survey_total_responses, description: preview.survey_total_responses ? "Respuestas importadas para analisis." : "Sin respuestas importadas." }
  ];
}

export function formatReportDate(value?: string | null) {
  return value ? new Date(value).toLocaleString("es-CL") : "Sin fecha";
}

export function getReportFilename(report: Pick<Report, "id" | "title">) {
  const slug = report.title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `ecoevent-360-${slug || "reporte"}-${report.id}.pdf`;
}

export { buildEventDashboardFromFallbackData };
