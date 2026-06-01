"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { SupervisorEventCard } from "@/components/supervisor/SupervisorEventCard";
import { SupervisorQuickActions } from "@/components/supervisor/SupervisorQuickActions";
import { getEvents } from "@/lib/api/events";
import { getMyTasks } from "@/lib/api/tasks";
import type { Event } from "@/types/event";
import type { Task } from "@/types/task";

export default function SupervisorEventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventData, taskData] = await Promise.all([getEvents({ page: 1, limit: 100 }), getMyTasks({ page: 1, limit: 100 })]);
      setEvents(eventData.items);
      setTasks(taskData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const pendingByEvent = useMemo(() => tasks.reduce<Record<string, number>>((acc, task) => {
    if (task.status !== "COMPLETED") acc[task.event_id] = (acc[task.event_id] || 0) + 1;
    return acc;
  }, {}), [tasks]);

  return (
    <RoleGuard roles={["SUPERVISOR"]}>
      <div className="space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase text-primary">Supervision</p>
          <h1 className="mt-1 text-3xl font-bold">Eventos asignados</h1>
          <p className="mt-2 text-muted-foreground">Gestiona zonas, personal y tareas de tus eventos operativos.</p>
        </div>
        <SupervisorQuickActions />
        {loading ? <LoadingState label="Cargando eventos..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && !error && events.length === 0 ? <EmptyState title="Sin eventos asignados" description="Cuando seas asignado a eventos, apareceran en esta vista." /> : null}
        <div className="grid gap-4 lg:grid-cols-2">
          {events.map((event) => <SupervisorEventCard key={event.id} event={event} pendingTasks={pendingByEvent[event.id] || 0} />)}
        </div>
      </div>
    </RoleGuard>
  );
}
