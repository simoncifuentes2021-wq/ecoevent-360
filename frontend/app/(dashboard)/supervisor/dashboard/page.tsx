"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { AlertTriangle, CalendarClock, CheckCircle2, ClipboardList, PackageCheck, ShieldAlert, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { SupervisorEventCard } from "@/components/supervisor/SupervisorEventCard";
import { SupervisorQuickActions } from "@/components/supervisor/SupervisorQuickActions";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { getEvents } from "@/lib/api/events";
import { getEventIncidents } from "@/lib/api/incidents";
import { getLogisticsOrders } from "@/lib/api/logistics-orders";
import { getMyTasks } from "@/lib/api/tasks";
import { getWorkerDashboard } from "@/lib/api/worker";
import type { Event } from "@/types/event";
import type { Incident } from "@/types/incident";
import type { LogisticsOrder, LogisticsOrderStatus } from "@/types/logistics-order";
import type { Task } from "@/types/task";

const logisticsStatusLabels: Record<LogisticsOrderStatus, string> = {
  REQUESTED: "Solicitado",
  ASSIGNED: "Asignado",
  STOCK_REVIEW: "Revision stock",
  RESERVED: "Stock reservado",
  INSUFFICIENT_STOCK: "Stock insuficiente",
  IN_PREPARATION: "En preparacion",
  LOADED: "Cargado",
  OUT_OF_WAREHOUSE: "Salida de bodega",
  DELIVERED: "Entregado",
  PARTIALLY_DELIVERED: "Entrega parcial",
  OUTCOME_PENDING: "Resultado pendiente",
  OUTCOME_RECORDED: "Resultados registrados",
  WITH_DIFFERENCES: "Con diferencias",
  CLOSED: "Cerrado",
  OBSERVED: "Observado",
  CANCELLED: "Cancelado"
};

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
  const [logisticsOrders, setLogisticsOrders] = useState<LogisticsOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [dashboard, eventData, taskData, logisticsData] = await Promise.all([
        getWorkerDashboard().catch(() => null),
        getEvents({ page: 1, limit: 100 }),
        getMyTasks({ page: 1, limit: 100 }),
        getLogisticsOrders({ page: 1, limit: 100 }).catch(() => ({ items: [] as LogisticsOrder[], total: 0, page: 1, limit: 100 }))
      ]);

      const eventItems = dashboard?.upcoming_events?.length ? dashboard.upcoming_events : eventData.items;
      setEvents(eventItems);
      setTasks(taskData.items);
      setLogisticsOrders(logisticsData.items);

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
    const activeLogisticsOrders = logisticsOrders.filter((order) => !["CLOSED", "CANCELLED"].includes(order.status)).length;
    return { pending, inProgress, completed, openIncidents, criticalIncidents, activeLogisticsOrders };
  }, [incidents, logisticsOrders, tasks]);

  const pendingByEvent = useMemo(() => tasks.reduce<Record<string, number>>((acc, task) => {
    if (task.status !== "COMPLETED") acc[task.event_id] = (acc[task.event_id] || 0) + 1;
    return acc;
  }, {}), [tasks]);

  const urgentTasks = tasks.filter((task) => task.status !== "COMPLETED" && (task.priority === "HIGH" || task.priority === "CRITICAL")).slice(0, 5);
  const openIncidents = incidents.filter((incident) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(incident.status)).slice(0, 5);
  const recentLogisticsOrders = logisticsOrders
    .filter((order) => !["CLOSED", "CANCELLED"].includes(order.status))
    .slice(0, 5);

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
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
              <MetricCard icon={<Sparkles className="h-6 w-6" />} label="Eventos asignados" value={events.length} />
              <MetricCard icon={<ClipboardList className="h-6 w-6" />} label="Tareas pendientes" value={metrics.pending} />
              <MetricCard icon={<CalendarClock className="h-6 w-6" />} label="En progreso" value={metrics.inProgress} />
              <MetricCard icon={<CheckCircle2 className="h-6 w-6" />} label="Completadas" value={metrics.completed} />
              <MetricCard icon={<ShieldAlert className="h-6 w-6" />} label="Incidencias abiertas" value={metrics.openIncidents} />
              <MetricCard icon={<PackageCheck className="h-6 w-6" />} label="Pedidos logisticos" value={metrics.activeLogisticsOrders} />
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

            <section className="rounded-3xl border bg-white p-5 shadow-sm">
              <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                <div>
                  <h2 className="text-lg font-bold text-slate-950">Pedidos logisticos de tus eventos</h2>
                  <p className="text-sm text-slate-600">Solo se muestran pedidos asociados a eventos donde estas asignado.</p>
                </div>
                <Link href="/supervisor/eventos">
                  <Button variant="secondary">Ver eventos</Button>
                </Link>
              </div>
              {recentLogisticsOrders.length === 0 ? (
                <EmptyState title="Sin pedidos logisticos activos" description="Cuando crees o se registren pedidos en tus eventos asignados, apareceran aqui." />
              ) : null}
              <div className="mt-4 grid gap-3">
                {recentLogisticsOrders.map((order) => (
                  <Link
                    className="grid gap-3 rounded-2xl border p-4 transition hover:bg-emerald-50 md:grid-cols-[1fr_auto] md:items-center"
                    href={`/supervisor/logistica/pedidos/${order.id}`}
                    key={order.id}
                  >
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-slate-950">{order.title}</p>
                      <p className="mt-1 text-sm text-slate-600">
                        {order.event?.name || "Evento asignado"} - {order.warehouse?.name || "Sin bodega"}
                      </p>
                      <p className="mt-1 text-xs text-slate-500">
                        Operador: {order.assigned_operator?.full_name || "Sin operador"} - Productos: {order.items.length}
                      </p>
                    </div>
                    <Badge tone={logisticsBadgeTone(order.status)}>{logisticsStatusLabels[order.status]}</Badge>
                  </Link>
                ))}
              </div>
            </section>

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

function logisticsBadgeTone(status: LogisticsOrderStatus) {
  if (status === "CANCELLED") return "danger";
  if (status === "INSUFFICIENT_STOCK" || status === "WITH_DIFFERENCES") return "warning";
  if (status === "CLOSED") return "neutral";
  return "success";
}
