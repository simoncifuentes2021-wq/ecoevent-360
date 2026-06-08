import { normalizeCarbonSummary } from "@/lib/normalizers/carbon";
import { normalizeWasteSummary } from "@/lib/normalizers/waste";
import { statusLabel } from "@/lib/status-labels";
import type { AdminDashboard, ClientDashboard, DashboardBucket, EventDashboard, WorkerDashboard } from "@/types/dashboard";
import type { Event } from "@/types/event";
import type { Incident } from "@/types/incident";
import type { Survey } from "@/types/survey";
import type { Task } from "@/types/task";

function asNumber(value: unknown, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function buckets(value: unknown): DashboardBucket[] {
  if (Array.isArray(value)) return value.map((item) => ({ name: statusLabel(String(item.name ?? item.status ?? item.category ?? "Sin dato")), value: asNumber(item.value ?? item.count ?? item.total) }));
  if (value && typeof value === "object") return Object.entries(value).map(([name, count]) => ({ name: statusLabel(name), value: asNumber(count) }));
  return [];
}

function countBy<T>(items: T[], getKey: (item: T) => string | undefined | null) {
  const map = new Map<string, number>();
  items.forEach((item) => {
    const key = getKey(item) || "Sin dato";
    map.set(key, (map.get(key) ?? 0) + 1);
  });
  return Array.from(map.entries()).map(([name, value]) => ({ name, value }));
}

export function normalizeAdminDashboard(raw: unknown): AdminDashboard {
  const data = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
  return {
    total_clients: asNumber(data.total_clients),
    total_users: asNumber(data.total_users),
    total_events: asNumber(data.total_events),
    active_events: asNumber(data.active_events),
    finished_events: asNumber(data.finished_events),
    cancelled_events: asNumber(data.cancelled_events),
    open_incidents: asNumber(data.open_incidents),
    resolved_incidents: asNumber(data.resolved_incidents),
    pending_tasks: asNumber(data.pending_tasks),
    completed_tasks: asNumber(data.completed_tasks),
    completed_tasks_rate: asNumber(data.completed_tasks_rate),
    total_waste_kg: asNumber(data.total_waste_kg),
    recovered_waste_kg: asNumber(data.recovered_waste_kg),
    waste_recovery_rate: asNumber(data.waste_recovery_rate),
    total_carbon_kgco2e: asNumber(data.total_carbon_kgco2e),
    total_carbon_tco2e: asNumber(data.total_carbon_tco2e),
    latest_events: Array.isArray(data.latest_events) ? data.latest_events as Event[] : [],
    latest_incidents: Array.isArray(data.latest_incidents) ? data.latest_incidents as AdminDashboard["latest_incidents"] : [],
    events_by_status: buckets(data.events_by_status),
    tasks_by_status: buckets(data.tasks_by_status),
    incidents_by_status: buckets(data.incidents_by_status),
    waste_by_destination: buckets(data.waste_by_destination),
    carbon_by_category: buckets(data.carbon_by_category),
    recent_activity: Array.isArray(data.recent_activity) ? data.recent_activity as AdminDashboard["recent_activity"] : []
  };
}

export function normalizeEventDashboard(raw: unknown): EventDashboard {
  const data = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
  return {
    event: data.event as Event | undefined,
    tasks: {
      total: asNumber((data.tasks as Record<string, unknown> | undefined)?.total),
      completed: asNumber((data.tasks as Record<string, unknown> | undefined)?.completed),
      completion_rate: asNumber((data.tasks as Record<string, unknown> | undefined)?.completion_rate),
      by_status: buckets((data.tasks as Record<string, unknown> | undefined)?.by_status)
    },
    incidents: {
      total: asNumber((data.incidents as Record<string, unknown> | undefined)?.total),
      open: asNumber((data.incidents as Record<string, unknown> | undefined)?.open),
      resolved: asNumber((data.incidents as Record<string, unknown> | undefined)?.resolved),
      by_status: buckets((data.incidents as Record<string, unknown> | undefined)?.by_status),
      by_priority: buckets((data.incidents as Record<string, unknown> | undefined)?.by_priority)
    },
    waste: {
      total_kg: asNumber((data.waste as Record<string, unknown> | undefined)?.total_kg),
      recovered_kg: asNumber((data.waste as Record<string, unknown> | undefined)?.recovered_kg),
      landfill_kg: asNumber((data.waste as Record<string, unknown> | undefined)?.landfill_kg),
      recovery_rate: asNumber((data.waste as Record<string, unknown> | undefined)?.recovery_rate),
      by_type: buckets((data.waste as Record<string, unknown> | undefined)?.by_type),
      by_destination: buckets((data.waste as Record<string, unknown> | undefined)?.by_destination),
      by_zone: buckets((data.waste as Record<string, unknown> | undefined)?.by_zone)
    },
    carbon: {
      total_kgco2e: asNumber((data.carbon as Record<string, unknown> | undefined)?.total_kgco2e),
      total_tco2e: asNumber((data.carbon as Record<string, unknown> | undefined)?.total_tco2e),
      kgco2e_per_attendee: asNumber((data.carbon as Record<string, unknown> | undefined)?.kgco2e_per_attendee),
      by_category: buckets((data.carbon as Record<string, unknown> | undefined)?.by_category),
      by_scope: buckets((data.carbon as Record<string, unknown> | undefined)?.by_scope)
    },
    survey: {
      total_responses: asNumber((data.survey as Record<string, unknown> | undefined)?.total_responses),
      average_rating: asNumber((data.survey as Record<string, unknown> | undefined)?.average_rating),
      recommendation_rate: asNumber((data.survey as Record<string, unknown> | undefined)?.recommendation_rate),
      cleaning_average: asNumber((data.survey as Record<string, unknown> | undefined)?.cleaning_average),
      bathroom_average: asNumber((data.survey as Record<string, unknown> | undefined)?.bathroom_average),
      main_problems: buckets((data.survey as Record<string, unknown> | undefined)?.main_problems),
      responses_by_zone: buckets((data.survey as Record<string, unknown> | undefined)?.responses_by_zone),
      main_problem: String((data.survey as Record<string, unknown> | undefined)?.main_problem ?? "Sin dato")
    },
    evidences: { total: asNumber((data.evidences as Record<string, unknown> | undefined)?.total), recent: [] },
    critical_zones: buckets(data.critical_zones),
    recommendations: Array.isArray(data.recommendations) ? data.recommendations.map(String) : [],
    alerts: data.alerts as EventDashboard["alerts"]
  };
}

export function normalizeClientDashboard(raw: unknown): ClientDashboard {
  const data = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
  return {
    total_events: asNumber(data.total_events),
    active_events: asNumber(data.active_events),
    reports_available: asNumber(data.reports_available),
    total_waste_kg: asNumber(data.total_waste_kg),
    total_carbon_tco2e: asNumber(data.total_carbon_tco2e),
    latest_surveys: Array.isArray(data.latest_surveys) ? data.latest_surveys : [],
    events: Array.isArray(data.events) ? data.events as Event[] : []
  };
}

export function normalizeWorkerDashboard(raw: unknown): WorkerDashboard {
  const data = raw && typeof raw === "object" ? raw as Record<string, unknown> : {};
  return {
    assigned_events: asNumber(data.assigned_events),
    pending_tasks: asNumber(data.pending_tasks),
    in_progress_tasks: asNumber(data.in_progress_tasks),
    completed_tasks: asNumber(data.completed_tasks),
    overdue_tasks: asNumber(data.overdue_tasks),
    assigned_incidents: asNumber(data.assigned_incidents),
    open_incidents: asNumber(data.open_incidents),
    resolved_incidents: asNumber(data.resolved_incidents),
    upcoming_events: Array.isArray(data.upcoming_events) ? data.upcoming_events as Event[] : [],
    today_tasks: Array.isArray(data.today_tasks) ? data.today_tasks : [],
    upcoming_tasks: Array.isArray(data.upcoming_tasks) ? data.upcoming_tasks : [],
    assigned_events_list: Array.isArray(data.assigned_events_list) ? data.assigned_events_list as WorkerDashboard["assigned_events_list"] : [],
    recent_incidents: Array.isArray(data.recent_incidents) ? data.recent_incidents : []
  };
}

export function buildEventDashboardFromFallbackData(data: {
  event?: Event;
  tasks?: Task[];
  incidents?: Incident[];
  wasteSummary?: unknown;
  carbonSummary?: unknown;
  surveys?: Survey[];
}): EventDashboard {
  const tasks = data.tasks ?? [];
  const incidents = data.incidents ?? [];
  const waste = normalizeWasteSummary(data.wasteSummary);
  const carbon = normalizeCarbonSummary(data.carbonSummary);
  const completed = tasks.filter((task) => task.status === "COMPLETED").length;
  const resolved = incidents.filter((incident) => incident.status === "RESOLVED" || incident.status === "CLOSED").length;
  const activeSurveys = (data.surveys ?? []).filter((survey) => survey.status === "ACTIVE").length;

  return {
    event: data.event,
    tasks: { total: tasks.length, completed, completion_rate: tasks.length ? Math.round((completed / tasks.length) * 100) : 0, by_status: countBy(tasks, (task) => task.status) },
    incidents: {
      total: incidents.length,
      open: incidents.filter((incident) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(incident.status)).length,
      resolved,
      by_status: countBy(incidents, (incident) => incident.status),
      by_priority: countBy(incidents, (incident) => incident.priority)
    },
    waste: { total_kg: waste.total_kg, recovered_kg: waste.recovered_kg, landfill_kg: 0, recovery_rate: waste.recovery_rate, by_type: [], by_destination: waste.by_destination, by_zone: [] },
    carbon: { total_kgco2e: carbon.total_kg_co2e, total_tco2e: carbon.total_ton_co2e, kgco2e_per_attendee: carbon.kg_co2e_per_attendee, by_category: carbon.by_category, by_scope: [] },
    survey: { total_responses: activeSurveys, average_rating: 0, recommendation_rate: 0, cleaning_average: 0, bathroom_average: 0, main_problems: [], responses_by_zone: [], main_problem: activeSurveys ? "Encuestas activas" : "Sin encuestas" },
    evidences: { total: 0, recent: [] },
    critical_zones: [],
    recommendations: [],
    alerts: { open: 0, critical: 0, recent: [] }
  };
}

export function formatDashboardPercentage(value: number) {
  return `${Math.round(value)}%`;
}

export function formatDashboardNumber(value: number) {
  return new Intl.NumberFormat("es-CL").format(value);
}
