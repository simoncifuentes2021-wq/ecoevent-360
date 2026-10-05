"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardErrorState } from "@/components/dashboard/DashboardErrorState";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";
import { EventDashboardCards } from "@/components/dashboard/EventDashboardCards";
import { EventControlSummary } from "@/components/dashboard/EventControlSummary";
import { EventEnvironmentalCharts } from "@/components/dashboard/EventEnvironmentalCharts";
import { EventExecutiveHeader } from "@/components/dashboard/EventExecutiveHeader";
import { EventOperationalCharts } from "@/components/dashboard/EventOperationalCharts";
import { EventRecentActivity } from "@/components/dashboard/EventRecentActivity";
import { EventSurveyDashboard } from "@/components/dashboard/EventSurveyDashboard";
import { getEventDashboard } from "@/lib/api/dashboards";
import { normalizeEventDashboard } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";
import type { Event } from "@/types/event";

export function EventDashboardTab({ eventId, event }: { eventId: string; event?: Event }) {
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

  const hasSurvey = dashboard.survey.total_responses > 0;

  return (
    <div className="space-y-7">
      {error ? <DashboardErrorState message={error} onRetry={load} /> : null}
      <EventExecutiveHeader dashboard={dashboard} event={event} />
      <EventDashboardCards dashboard={dashboard} />
      <EventControlSummary dashboard={dashboard} />
      <section className="space-y-4">
        <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Análisis de desempeño</p><h2 className="mt-1 text-xl font-bold tracking-tight text-slate-950">Operación e impacto</h2><p className="mt-1 text-sm text-slate-600">Indicadores comparables para entender el avance y el impacto total del evento.</p></div>
        <EventOperationalCharts incidentsByStatus={dashboard.incidents.by_status} tasksByStatus={dashboard.tasks.by_status} />
        <EventEnvironmentalCharts carbonByCategory={dashboard.carbon.by_category} wasteByDestination={dashboard.waste.by_destination} />
      </section>
      {hasSurvey ? <div className="grid gap-5 xl:grid-cols-[1.05fr_0.95fr]"><EventSurveyDashboard dashboard={dashboard} /><EventRecentActivity dashboard={dashboard} /></div> : <EventRecentActivity dashboard={dashboard} />}
    </div>
  );
}
