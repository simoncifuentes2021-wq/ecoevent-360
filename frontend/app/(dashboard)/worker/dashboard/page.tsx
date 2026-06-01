"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarClock, ChevronRight } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { WorkerDashboardCards, WorkerQuickActions } from "@/components/worker/WorkerDashboardCards";
import { useToast } from "@/components/common/ToastProvider";
import { getWorkerDashboard } from "@/lib/api/worker";
import { getEvents } from "@/lib/api/events";
import { getEventIncidents } from "@/lib/api/incidents";
import { getMyTasks } from "@/lib/api/tasks";
import { useAuth } from "@/hooks/useAuth";
import type { Event } from "@/types/event";
import type { Incident } from "@/types/incident";
import type { Task } from "@/types/task";

function isToday(value?: string | null) {
  if (!value) return false;
  const date = new Date(value);
  const now = new Date();
  return date.toDateString() === now.toDateString();
}

function shortDate(value?: string | null) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value));
}

export default function WorkerDashboardPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, taskResponse, eventResponse] = await Promise.all([
        getWorkerDashboard().catch(() => null),
        getMyTasks({ page: 1, limit: 100 }),
        getEvents({ page: 1, limit: 50 })
      ]);

      const taskItems = taskResponse.items;
      const eventItems = dashboard?.upcoming_events?.length ? dashboard.upcoming_events : eventResponse.items;
      setTasks(taskItems);
      setEvents(eventItems);

      const selectedEventId = eventItems[0]?.id || taskItems[0]?.event_id || "";
      if (selectedEventId) {
        const incidentResponse = await getEventIncidents(selectedEventId, { page: 1, limit: 5 }).catch(() => null);
        setIncidents(incidentResponse?.items ?? []);
      } else {
        setIncidents([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar tu panel.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const counts = useMemo(() => {
    const pending = tasks.filter((t) => t.status === "PENDING").length;
    const inProgress = tasks.filter((t) => t.status === "IN_PROGRESS").length;
    const completedToday = tasks.filter((t) => t.status === "COMPLETED" && isToday(t.completed_at)).length;
    const critical = tasks.filter((t) => t.priority === "CRITICAL" && t.status !== "COMPLETED").length;
    return { pending, inProgress, completedToday, critical };
  }, [tasks]);

  const upcoming = useMemo(() => events.slice(0, 3), [events]);
  const recentIncidents = useMemo(() => incidents.slice(0, 3), [incidents]);

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell
        title={`Hola${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
        description="Resumen rapido para operar en terreno."
      >
        {loading ? <LoadingState label="Cargando tu resumen..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}

        {!loading && !error ? (
          <div className="space-y-5">
            <WorkerDashboardCards {...counts} />

            <section className="space-y-3">
              <h2 className="text-base font-bold text-slate-950">Acciones rapidas</h2>
              <WorkerQuickActions />
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-950">Proximos eventos</h2>
                <Link href="/worker/eventos">
                  <Button size="sm" variant="secondary">
                    Ver todos <ChevronRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {upcoming.length === 0 ? (
                <EmptyState title="No tienes eventos asignados" description="Cuando te asignen un evento, aparecera aqui." />
              ) : (
                <div className="space-y-2">
                  {upcoming.map((event) => (
                    <Link
                      className="flex items-center justify-between gap-3 rounded-3xl border bg-white p-4 shadow-sm hover:bg-emerald-50"
                      href={`/worker/eventos/${event.id}`}
                      key={event.id}
                      onClick={() => toast({ tone: "success", title: "Abriendo evento", description: event.name })}
                    >
                      <div className="min-w-0">
                        <p className="truncate font-semibold text-slate-950">{event.name}</p>
                        <p className="mt-1 flex items-center gap-2 text-sm text-slate-600">
                          <CalendarClock className="h-4 w-4 text-emerald-700" />
                          {shortDate(event.start_date)}
                        </p>
                      </div>
                      <ChevronRight className="h-5 w-5 text-slate-400" />
                    </Link>
                  ))}
                </div>
              )}
            </section>

            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-bold text-slate-950">Incidencias recientes</h2>
                <Link href="/worker/reportar-incidencia">
                  <Button size="sm" variant="secondary">
                    Reportar <ChevronRight className="h-4 w-4" />
                  </Button>
                </Link>
              </div>

              {recentIncidents.length === 0 ? (
                <EmptyState title="Sin incidencias recientes" description="Si detectas un problema, reportalo en segundos." />
              ) : (
                <div className="space-y-2">
                  {recentIncidents.map((incident) => (
                    <Link
                      className="rounded-3xl border bg-white p-4 shadow-sm hover:bg-emerald-50"
                      href={`/worker/incidencias/${incident.id}`}
                      key={incident.id}
                    >
                      <p className="font-semibold text-slate-950">{incident.title}</p>
                      <p className="mt-1 text-sm text-slate-600">{incident.zone?.name || "Sin zona"} - {incident.status}</p>
                    </Link>
                  ))}
                </div>
              )}
            </section>
          </div>
        ) : null}
      </MobileShell>
    </RoleGuard>
  );
}
