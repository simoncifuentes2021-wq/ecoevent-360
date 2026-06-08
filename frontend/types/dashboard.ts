import type { Event } from "@/types/event";

export type DashboardBucket = {
  name: string;
  value: number;
};

export type AdminDashboard = {
  total_clients: number;
  total_users: number;
  total_events: number;
  active_events: number;
  finished_events: number;
  cancelled_events: number;
  open_incidents: number;
  resolved_incidents: number;
  pending_tasks: number;
  completed_tasks: number;
  completed_tasks_rate: number;
  total_waste_kg: number;
  recovered_waste_kg: number;
  waste_recovery_rate: number;
  total_carbon_kgco2e: number;
  total_carbon_tco2e: number;
  latest_events: Event[];
  latest_incidents: Array<{ id: string; event_id: string; event_name?: string | null; title: string; priority: string; status: string; created_at: string }>;
  events_by_status: DashboardBucket[];
  tasks_by_status: DashboardBucket[];
  incidents_by_status: DashboardBucket[];
  waste_by_destination: DashboardBucket[];
  carbon_by_category: DashboardBucket[];
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
    recovered_kg: number;
    landfill_kg: number;
    recovery_rate: number;
    by_type: DashboardBucket[];
    by_destination: DashboardBucket[];
    by_zone: DashboardBucket[];
  };
  carbon: {
    total_kgco2e: number;
    total_tco2e: number;
    kgco2e_per_attendee: number;
    by_category: DashboardBucket[];
    by_scope: DashboardBucket[];
  };
  survey: {
    total_responses: number;
    average_rating: number;
    recommendation_rate: number;
    cleaning_average: number;
    bathroom_average: number;
    main_problems: DashboardBucket[];
    responses_by_zone: DashboardBucket[];
    main_problem?: string;
  };
  evidences: {
    total: number;
    recent: Array<{ id: string; description?: string | null; file_url?: string | null; created_at?: string }>;
  };
  critical_zones: DashboardBucket[];
  recommendations: string[];
  alerts?: {
    open: number;
    critical: number;
    recent: unknown[];
  };
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
  assigned_events: number;
  pending_tasks: number;
  in_progress_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  assigned_incidents: number;
  open_incidents: number;
  resolved_incidents: number;
  upcoming_events: Event[];
  today_tasks: unknown[];
  upcoming_tasks: unknown[];
  assigned_events_list: Array<{
    id: string;
    name: string;
    status: Event["status"];
    start_date: string;
    end_date: string;
    location_name?: string | null;
    pending_tasks: number;
    open_incidents: number;
  }>;
  recent_incidents: unknown[];
};
