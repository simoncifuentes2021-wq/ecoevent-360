import { api } from "@/lib/api";
import type { AdminDashboard, ClientDashboard, EventDashboard, WorkerDashboard } from "@/types/dashboard";

export function getAdminDashboard() {
  return api.get<AdminDashboard | Record<string, unknown>>("/dashboard/admin");
}

export function getClientDashboard() {
  return api.get<ClientDashboard | Record<string, unknown>>("/dashboard/client");
}

export function getWorkerDashboard() {
  return api.get<WorkerDashboard | Record<string, unknown>>("/dashboard/worker");
}

export function getEventDashboard(eventId: string) {
  return api.get<EventDashboard | Record<string, unknown>>(`/events/${eventId}/dashboard`);
}
