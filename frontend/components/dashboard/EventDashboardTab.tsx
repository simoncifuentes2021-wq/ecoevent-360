"use client";

import { useCallback, useEffect, useState } from "react";

import { DashboardErrorState } from "@/components/dashboard/DashboardErrorState";
import { DashboardSkeleton } from "@/components/dashboard/DashboardSkeleton";
import { EventDashboardCards } from "@/components/dashboard/EventDashboardCards";
import { EventEnvironmentalCharts } from "@/components/dashboard/EventEnvironmentalCharts";
import { EventOperationalCharts } from "@/components/dashboard/EventOperationalCharts";
import { EventRecentActivity } from "@/components/dashboard/EventRecentActivity";
import { EventSurveyDashboard } from "@/components/dashboard/EventSurveyDashboard";
import { getCarbonSummary } from "@/lib/api/carbon";
import { getEventDashboard } from "@/lib/api/dashboards";
import { getEvent } from "@/lib/api/events";
import { getEventIncidents } from "@/lib/api/incidents";
import { getEventSurveys } from "@/lib/api/surveys";
import { getEventTasks } from "@/lib/api/tasks";
import { getWasteSummary } from "@/lib/api/waste";
import { buildEventDashboardFromFallbackData, normalizeEventDashboard } from "@/lib/normalizers/dashboard";
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
    } catch {
      const [eventData, tasks, incidents, wasteSummary, carbonSummary, surveys] = await Promise.allSettled([
        event ? Promise.resolve(event) : getEvent(eventId),
        getEventTasks(eventId),
        getEventIncidents(eventId),
        getWasteSummary(eventId),
        getCarbonSummary(eventId),
        getEventSurveys(eventId)
      ]);
      setDashboard(buildEventDashboardFromFallbackData({
        event: eventData.status === "fulfilled" ? eventData.value : event,
        tasks: tasks.status === "fulfilled" ? tasks.value.items : [],
        incidents: incidents.status === "fulfilled" ? incidents.value.items : [],
        wasteSummary: wasteSummary.status === "fulfilled" ? wasteSummary.value : null,
        carbonSummary: carbonSummary.status === "fulfilled" ? carbonSummary.value : null,
        surveys: surveys.status === "fulfilled" ? surveys.value.items : []
      }));
      const anyFulfilled = [eventData, tasks, incidents, wasteSummary, carbonSummary, surveys].some((item) => item.status === "fulfilled");
      if (!anyFulfilled) setError("El dashboard avanzado aun no esta disponible en el backend.");
    } finally {
      setLoading(false);
    }
  }, [event, eventId]);

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
