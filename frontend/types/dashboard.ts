import type { Event } from "@/types/event";

export type DashboardBucket = {
  name: string;
  value: number;
};

export type AdminDashboard = {
  total_clients: number;
  total_events: number;
  active_events: number;
  finished_events: number;
  open_incidents: number;
  completed_tasks_rate: number;
  total_waste_kg: number;
  total_carbon_tco2e: number;
  latest_events: Event[];
  events_by_status: DashboardBucket[];
  recent_activity: Array<{ title: string; description?: string; created_at?: string }>;
};

export type EventDashboard = {
  event?: Event;
  tasks: {
    total: number;
    completed: number;
    completion_rate: number;
    by_status: DashboardBucket[];
  };
  incidents: {
    total: number;
    open: number;
    resolved: number;
    by_status: DashboardBucket[];
    by_priority: DashboardBucket[];
  };
  waste: {
    total_kg: number;
    recovery_rate: number;
    by_destination: DashboardBucket[];
  };
  carbon: {
    total_tco2e: number;
    kgco2e_per_attendee: number;
    by_category: DashboardBucket[];
  };
  survey: {
    total_responses: number;
    average_rating: number;
    recommendation_rate: number;
    main_problem?: string;
  };
  evidences: {
    total: number;
    recent: Array<{ id: string; description?: string | null; file_url?: string | null; created_at?: string }>;
  };
  critical_zones: DashboardBucket[];
  recommendations: string[];
};

export type ClientDashboard = {
  total_events: number;
  active_events: number;
  reports_available: number;
  total_waste_kg: number;
  total_carbon_tco2e: number;
  latest_surveys: unknown[];
  events: Event[];
};

export type WorkerDashboard = {
  pending_tasks: number;
  completed_tasks: number;
  assigned_incidents: number;
  upcoming_events: Event[];
  today_tasks: unknown[];
};
