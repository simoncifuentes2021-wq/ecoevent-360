import type { ClientDashboard, ClientIndicatorByEvent } from "@/types/clientDashboard";
import type { Event } from "@/types/event";

function asNumber(value: unknown, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

export function normalizeClientIndicators(raw: unknown): ClientIndicatorByEvent[] {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => {
    const value = item && typeof item === "object" ? item as Record<string, unknown> : {};
    return {
      event_id: String(value.event_id ?? ""),
      event_name: String(value.event_name ?? "Evento"),
      waste_total_kg: asNumber(value.waste_total_kg),
      waste_recovery_rate: asNumber(value.waste_recovery_rate),
      carbon_tco2e: asNumber(value.carbon_tco2e),
      kgco2e_per_attendee: asNumber(value.kgco2e_per_attendee),
      average_rating: asNumber(value.average_rating),
      incidents_total: asNumber(value.incidents_total),
      tasks_completion_rate: asNumber(value.tasks_completion_rate)
    };
  });
}

export function normalizeClientDashboard(raw: unknown): ClientDashboard {
  const data = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
  return {
    total_events: asNumber(data.total_events),
    active_events: asNumber(data.active_events),
    finished_events: asNumber(data.finished_events),
    reports_available: asNumber(data.reports_available),
    total_waste_kg: asNumber(data.total_waste_kg),
    recovered_waste_kg: asNumber(data.recovered_waste_kg),
    recovery_rate: asNumber(data.recovery_rate),
    total_carbon_tco2e: asNumber(data.total_carbon_tco2e),
    average_satisfaction: asNumber(data.average_satisfaction),
    latest_events: Array.isArray(data.latest_events) ? data.latest_events as Event[] : [],
    latest_reports: Array.isArray(data.latest_reports) ? data.latest_reports as ClientDashboard["latest_reports"] : [],
    indicators_by_event: normalizeClientIndicators(data.indicators_by_event)
  };
}

export function buildClientDashboardFromEvents(events: Event[]): ClientDashboard {
  const active = events.filter((event) => ["PLANNING", "IN_PROGRESS"].includes(event.status)).length;
  const finished = events.filter((event) => ["FINISHED", "REPORT_DELIVERED"].includes(event.status)).length;
  return {
    total_events: events.length,
    active_events: active,
    finished_events: finished,
    reports_available: 0,
    total_waste_kg: 0,
    recovered_waste_kg: 0,
    recovery_rate: 0,
    total_carbon_tco2e: 0,
    average_satisfaction: 0,
    latest_events: events.slice(0, 5),
    latest_reports: [],
    indicators_by_event: events.map((event) => ({
      event_id: event.id,
      event_name: event.name,
      waste_total_kg: 0,
      waste_recovery_rate: 0,
      carbon_tco2e: 0,
      kgco2e_per_attendee: 0,
      average_rating: 0,
      incidents_total: 0,
      tasks_completion_rate: 0
    }))
  };
}

export function formatClientMetric(value: number) {
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 1 }).format(value);
}

export function formatClientPercentage(value: number) {
  return `${Math.round(value)}%`;
}
