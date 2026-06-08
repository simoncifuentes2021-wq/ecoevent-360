"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardErrorState } from "@/components/dashboard/DashboardErrorState";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";
import { EventDashboardCards } from "@/components/dashboard/EventDashboardCards";
import { EventEnvironmentalCharts } from "@/components/dashboard/EventEnvironmentalCharts";
import { EventOperationalCharts } from "@/components/dashboard/EventOperationalCharts";
import { EventRecentActivity } from "@/components/dashboard/EventRecentActivity";
import { EventSurveyDashboard } from "@/components/dashboard/EventSurveyDashboard";
import { getEventDashboard } from "@/lib/api/dashboards";
import { normalizeEventDashboard } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";
import type { Event } from "@/types/event";

export function EventDashboardTab({ eventId }: { eventId: string; event?: Event }) {
  const [dashboard, setDashboard] = useState<EventDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const raw = await getEventDashboard(eventId);
      setDashboard(normalizeEventDashboard(raw));
    } catch (err) {
      setDashboard(null);
      setError(err instanceof Error ? err.message : "No se pudo cargar el dashboard del evento.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <DashboardSkeleton />;
  if (!dashboard) return <DashboardErrorState message={error ?? undefined} onRetry={load} />;

  return (
    <div className="space-y-5">
      {error ? <DashboardErrorState message={error} onRetry={load} /> : null}
      <div>
        <h2 className="text-xl font-bold text-slate-950">Dashboard consolidado del evento</h2>
        <p className="text-sm text-slate-600">Indicadores operativos, ambientales y de experiencia publica.</p>
      </div>
      <EventDashboardCards dashboard={dashboard} />
      <EventOperationalCharts incidentsByStatus={dashboard.incidents.by_status} tasksByStatus={dashboard.tasks.by_status} />
      <EventEnvironmentalCharts carbonByCategory={dashboard.carbon.by_category} wasteByDestination={dashboard.waste.by_destination} />
      <EventSurveyDashboard dashboard={dashboard} />
      <EventRecentActivity dashboard={dashboard} />
    </div>
  );
}
