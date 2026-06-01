import { getClientDashboard as getDashboardEndpoint } from "@/lib/api/dashboards";
import { getEvents } from "@/lib/api/events";
import { buildClientDashboardFromEvents, normalizeClientDashboard } from "@/lib/normalizers/clientDashboard";

export async function getClientDashboard() {
  const raw = await getDashboardEndpoint();
  return normalizeClientDashboard(raw);
}

export async function getClientIndicatorsFallback() {
  const events = await getEvents({ page: 1, limit: 100 });
  return buildClientDashboardFromEvents(events.items);
}

export async function getClientReportsFallback() {
  const events = await getEvents({ page: 1, limit: 100 });
  return events.items;
}
