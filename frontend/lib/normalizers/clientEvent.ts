import { buildEventDashboardFromFallbackData, normalizeEventDashboard } from "@/lib/normalizers/dashboard";
import type { ClientEventDetail, ClientEventTab } from "@/types/clientEvent";

export function normalizeClientEvent(raw: unknown): ClientEventDetail {
  const data = raw && typeof raw === "object" ? raw as Partial<ClientEventDetail> : {};
  return {
    event: data.event,
    services: data.services ?? [],
    dashboard: data.dashboard ? normalizeEventDashboard(data.dashboard) : undefined,
    waste_summary: data.waste_summary,
    carbon_summary: data.carbon_summary,
    surveys_summary: data.surveys_summary,
    reports: data.reports ?? []
  };
}

export function normalizeClientEventDashboard(raw: unknown) {
  return normalizeEventDashboard(raw);
}

export function buildClientEventTabs(data: ClientEventDetail): ClientEventTab[] {
  return [
    { key: "resumen", label: "Resumen", visible: true },
    { key: "servicios", label: "Servicios", visible: true, count: data.services.length },
    { key: "avance", label: "Avance operativo", visible: true },
    { key: "incidencias", label: "Incidencias", visible: true },
    { key: "evidencias", label: "Evidencias", visible: true },
    { key: "residuos", label: "Residuos", visible: true },
    { key: "huella", label: "Huella", visible: true },
    { key: "encuestas", label: "Encuestas", visible: true },
    { key: "reportes", label: "Reportes", visible: true, count: data.reports.length }
  ];
}

export function sanitizeClientVisibleData<T>(data: T): T {
  return data;
}

export { buildEventDashboardFromFallbackData };
