"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarDays, FileText, Sparkles } from "lucide-react";

import { ClientEventCard } from "@/components/client/ClientEventCard";
import { ClientEventFilters } from "@/components/client/ClientEventFilters";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { getEvents } from "@/lib/api/events";
import type { Event } from "@/types/event";

export default function ClientEventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEvents({ page: 1, limit: 100 });
      setEvents(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar tus eventos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const activeEvents = useMemo(() => events.filter((event) => ["PLANNING", "IN_PROGRESS"].includes(event.status)).length, [events]);
  const finishedEvents = useMemo(() => events.filter((event) => ["FINISHED", "REPORT_DELIVERED"].includes(event.status)).length, [events]);
  const filtered = useMemo(() => events.filter((event) => {
    const text = `${event.name} ${event.event_type ?? ""} ${event.city ?? ""} ${event.region ?? ""}`.toLowerCase();
    return (!q || text.includes(q.toLowerCase())) && (!status || event.status === status);
  }), [events, q, status]);

  return (
    <RoleGuard roles={["CLIENT"]}>
      <div className="space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase text-primary">Portal cliente</p>
          <h1 className="mt-1 text-3xl font-bold">Mis eventos</h1>
          <p className="mt-2 text-muted-foreground">Consulta avances, evidencias, indicadores y reportes de tus eventos contratados.</p>
        </div>
        {loading ? <LoadingState label="Cargando tus eventos..." /> : null}
        {!loading && error ? <ErrorState message={error} title="No pudimos cargar tus eventos" onRetry={load} /> : null}
        {!loading && !error ? (
          <>
            <section className="grid gap-4 md:grid-cols-3">
              <KpiCard description="Asociados a tu cliente" icon={Sparkles} title="Total eventos" value={events.length} />
              <KpiCard description="Planificacion o ejecucion" icon={CalendarDays} title="Activos" tone="lime" value={activeEvents} />
              <KpiCard description="Finalizados o entregados" icon={FileText} title="Con cierre" tone="blue" value={finishedEvents} />
            </section>
            <ClientEventFilters q={q} status={status} onQChange={setQ} onStatusChange={setStatus} />
            {filtered.length ? <section className="grid gap-4 xl:grid-cols-2">{filtered.map((event) => <ClientEventCard event={event} key={event.id} />)}</section> : <EmptyState description="Tu usuario cliente no tiene eventos visibles con los filtros actuales." title="Sin eventos asignados" />}
          </>
        ) : null}
      </div>
    </RoleGuard>
  );
}
