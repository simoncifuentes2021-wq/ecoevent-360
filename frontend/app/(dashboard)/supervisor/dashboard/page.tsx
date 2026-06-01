"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, CalendarClock, CheckCircle2, ClipboardList, ShieldAlert, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { SupervisorEventCard } from "@/components/supervisor/SupervisorEventCard";
import { SupervisorQuickActions } from "@/components/supervisor/SupervisorQuickActions";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { getEvents } from "@/lib/api/events";
import { getEventIncidents } from "@/lib/api/incidents";
import { getMyTasks } from "@/lib/api/tasks";
import { getWorkerDashboard } from "@/lib/api/worker";
import type { Event } from "@/types/event";
import type { Incident } from "@/types/incident";
import type { Task } from "@/types/task";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value)) : "Sin fecha";
}

function MetricCard({ label, value, icon }: { label: string; value: number; icon: ReactNode }) {
  return (
    <div className="rounded-3xl border bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-black text-slate-950">{value}</p>
        </div>
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">{icon}</div>
      </div>
    </div>
  );
}

export default function SupervisorDashboardPage() {
  const { user } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, eventData, taskData] = await Promise.all([
        getWorkerDashboard().catch(() => null),
        getEvents({ page: 1, limit: 100 }),
        getMyTasks({ page: 1, limit: 100 })
      ]);

      const eventItems = dashboard?.upcoming_events?.length ? dashboard.upcoming_events : eventData.items;
      setEvents(eventItems);
      setTasks(taskData.items);

      const incidentData = await Promise.all(
        eventItems.slice(0, 8).map(async (event) => {
          const response = await getEventIncidents(event.id, { page: 1, limit: 50 }).catch(() => ({ items: [] as Incident[] }));
          return response.items;
        })
      );
      setIncidents(incidentData.flat());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el panel supervisor.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const metrics = useMemo(() => {
    const pending = tasks.filter((task) => task.status === "PENDING").length;
    const inProgress = tasks.filter((task) => task.status === "IN_PROGRESS").length;
    const completed = tasks.filter((task) => task.status === "COMPLETED").length;
    const openIncidents = incidents.filter((incident) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(incident.status)).length;
    const criticalIncidents = incidents.filter((incident) => incident.priority === "CRITICAL").length;
    return { pending, inProgress, completed, openIncidents, criticalIncidents };
  }, [incidents, tasks]);

  const pendingByEvent = useMemo(() => tasks.reduce<Record<string, number>>((acc, task) => {
    if (task.status !== "COMPLETED") acc[task.event_id] = (acc[task.event_id] || 0) + 1;
    return acc;
  }, {}), [tasks]);

  const urgentTasks = tasks.filter((task) => task.status !== "COMPLETED" && (task.priority === "HIGH" || task.priority === "CRITICAL")).slice(0, 5);
  const openIncidents = incidents.filter((incident) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(incident.status)).slice(0, 5);

  return (
    <RoleGuard roles={["SUPERVISOR"]}>
      <div className="space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase text-primary">Panel supervisor</p>
          <h1 className="mt-1 text-3xl font-bold">Hola{user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}</h1>
          <p className="mt-2 text-muted-foreground">Resumen operativo de tus eventos asignados, tareas e incidencias.</p>
        </div>

        {loading ? <LoadingState label="Cargando panel supervisor..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}

        {!loading && !error ? (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <MetricCard icon={<Sparkles className="h-6 w-6" />} label="Eventos asignados" value={events.length} />
              <MetricCard icon={<ClipboardList className="h-6 w-6" />} label="Tareas pendientes" value={metrics.pending} />
              <MetricCard icon={<CalendarClock className="h-6 w-6" />} label="En progreso" value={metrics.inProgress} />
              <MetricCard icon={<CheckCircle2 className="h-6 w-6" />} label="Completadas" value={metrics.completed} />
              <MetricCard icon={<ShieldAlert className="h-6 w-6" />} label="Incidencias abiertas" value={metrics.openIncidents} />
            </div>

            <SupervisorQuickActions />

            {events.length === 0 ? (
              <EmptyState title="Sin eventos asignados" description="Cuando seas asignado a un evento, lo veras en este panel." />
            ) : (
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-slate-950">Eventos asignados</h2>
                  <Link href="/supervisor/eventos"><Button variant="secondary">Ver todos</Button></Link>
                </div>
                <div className="grid gap-4 lg:grid-cols-2">
                  {events.slice(0, 4).map((event) => (
                    <SupervisorEventCard event={event} key={event.id} pendingTasks={pendingByEvent[event.id] || 0} />
                  ))}
                </div>
              </section>
            )}

            <div className="grid gap-4 lg:grid-cols-2">
              <section className="rounded-3xl border bg-white p-5 shadow-sm">
                <h2 className="text-lg font-bold text-slate-950">Tareas urgentes</h2>
                {urgentTasks.length === 0 ? <EmptyState title="Sin tareas urgentes" description="No hay tareas de alta prioridad pendientes." /> : null}
                <div className="mt-3 space-y-3">
                  {urgentTasks.map((task) => (
                    <Link className="block rounded-2xl border p-4 hover:bg-emerald-50" href={`/worker/tareas/${task.id}`} key={task.id}>
                      <p className="font-semibold text-slate-950">{task.title}</p>
                      <p className="mt-1 text-sm text-slate-600">{task.event?.name || "Evento asignado"} - {task.status}</p>
                    </Link>
                  ))}
                </div>
              </section>

              <section className="rounded-3xl border bg-white p-5 shadow-sm">
                <h2 className="text-lg font-bold text-slate-950">Incidencias abiertas</h2>
                {openIncidents.length === 0 ? <EmptyState title="Sin incidencias abiertas" description="No hay problemas abiertos en tus eventos." /> : null}
                <div className="mt-3 space-y-3">
                  {openIncidents.map((incident) => (
                    <Link className="block rounded-2xl border p-4 hover:bg-emerald-50" href={`/worker/incidencias/${incident.id}`} key={incident.id}>
                      <p className="flex items-center gap-2 font-semibold text-slate-950"><AlertTriangle className="h-4 w-4 text-amber-600" />{incident.title}</p>
                      <p className="mt-1 text-sm text-slate-600">{incident.zone?.name || "Sin zona"} - {date(incident.created_at)}</p>
                    </Link>
                  ))}
                </div>
              </section>
            </div>
          </div>
        ) : null}
      </div>
    </RoleGuard>
  );
}
