import type { Event } from "@/types/event";
import type { Report } from "@/types/report";

export type ClientIndicatorByEvent = {
  event_id: string;
  event_name: string;
  waste_total_kg: number;
  waste_recovery_rate: number;
  carbon_tco2e: number;
  kgco2e_per_attendee: number;
  average_rating: number;
  incidents_total: number;
  tasks_completion_rate: number;
};

export type ClientDashboard = {
  total_events: number;
  active_events: number;
  finished_events: number;
  reports_available: number;
  total_waste_kg: number;
  recovered_waste_kg: number;
  recovery_rate: number;
  total_carbon_tco2e: number;
  average_satisfaction: number;
  latest_events: Event[];
  latest_reports: Report[];
  indicators_by_event: ClientIndicatorByEvent[];
};
