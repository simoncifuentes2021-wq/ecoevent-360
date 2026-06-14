"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarClock, Eye, Plus, Search, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/useAuth";
import { getEvents } from "@/lib/api/events";
import { eventStatusLabels } from "@/lib/status-labels";
import type { Event, EventStatus } from "@/types/event";

const statuses: EventStatus[] = ["QUOTE", "PLANNING", "IN_PROGRESS", "FINISHED", "REPORT_DELIVERED", "CANCELLED"];

function eventHref(event: Event, role?: string | null) {
  if (role === "CLIENT") return `/client/eventos/${event.id}`;
  if (role === "SUPERVISOR") return `/supervisor/eventos/${event.id}`;
  if (role === "WORKER") return `/worker/eventos/${event.id}`;
  return `/admin/eventos/${event.id}`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value));
}

function isToday(event: Event) {
  const now = new Date();
  const start = new Date(event.start_date);
  const end = new Date(event.end_date);
  return start <= now && now <= end;
}

function isUpcoming(event: Event) {
  return new Date(event.start_date).getTime() > Date.now();
}

export default function EventsPage() {
  const { user } = useAuth();
  const [events, setEvents] = useState<Event[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const canCreate = user?.role === "SUPER_ADMIN" || user?.role === "ADMIN";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getEvents({ page: 1, limit: 100 });
      setEvents(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar eventos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    return events.filter((event) => {
      const text = `${event.name} ${event.client?.business_name || ""} ${event.city || ""} ${event.location_name || ""}`.toLowerCase();
      return (!q || text.includes(q.toLowerCase())) && (!status || event.status === status);
    });
  }, [events, q, status]);

  const todayEvents = filtered.filter(isToday);
  const upcomingEvents = filtered.filter(isUpcoming).slice(0, 6);
  const activeCount = events.filter((event) => ["PLANNING", "IN_PROGRESS"].includes(event.status)).length;
  const pendingCount = events.filter((event) => event.status === "QUOTE").length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Panel rápido de eventos"
        description="Acceso directo a los eventos reales, su estado y acciones operativas."
        actions={
          <div className="flex flex-wrap gap-2">
            {canCreate ? (
              <Link href="/admin/eventos/nuevo">
                <Button>
                  <Plus className="h-4 w-4" />
                  Crear evento
                </Button>
              </Link>
            ) : null}
            {canCreate ? (
              <Link href="/admin/eventos">
                <Button variant="secondary">
                  <Sparkles className="h-4 w-4" />
                  Administrar
                </Button>
              </Link>
            ) : null}
          </div>
        }
      />

      <div className="grid gap-3 md:grid-cols-3">
        <Metric label="Eventos visibles" value={events.length} />
        <Metric label="En planificación/operación" value={activeCount} />
        <Metric label="Cotizaciones" value={pendingCount} />
      </div>

      <Card>
        <CardContent className="grid gap-3 p-4 md:grid-cols-[1fr_240px]">
          <label className="relative">
            <Search className="absolute left-3 top-3 h-4 w-4 text-slate-400" />
            <Input className="pl-9" placeholder="Buscar por evento, cliente o ubicación" value={q} onChange={(event) => setQ(event.target.value)} />
          </label>
          <select className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Todos los estados</option>
            {statuses.map((item) => <option key={item} value={item}>{eventStatusLabels[item]}</option>)}
          </select>
        </CardContent>
      </Card>

      {loading ? <LoadingState label="Cargando eventos..." /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}

      {!loading && !error ? (
        <div className="grid gap-6 xl:grid-cols-[1fr_1.4fr]">
          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-950">Hoy</h2>
            {todayEvents.length === 0 ? (
              <EmptyState title="Sin eventos en curso" description="No hay eventos activos hoy con los filtros actuales." />
            ) : (
              <div className="grid gap-3">
                {todayEvents.map((event) => <EventCard event={event} key={event.id} role={user?.role} />)}
              </div>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-bold text-slate-950">Próximos eventos</h2>
            {upcomingEvents.length === 0 ? (
              <EmptyState title="Sin próximos eventos" description="No hay eventos próximos con los filtros actuales." />
            ) : (
              <div className="grid gap-3">
                {upcomingEvents.map((event) => <EventCard event={event} key={event.id} role={user?.role} />)}
              </div>
            )}
          </section>
        </div>
      ) : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm font-semibold text-slate-500">{label}</p>
        <p className="mt-2 text-3xl font-bold text-slate-950">{value}</p>
      </CardContent>
    </Card>
  );
}

function EventCard({ event, role }: { event: Event; role?: string | null }) {
  return (
    <Card>
      <CardContent className="grid gap-4 p-4 md:grid-cols-[1fr_auto] md:items-center">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <EventStatusBadge status={event.status} />
            <span className="text-sm font-semibold text-slate-500">{event.client?.business_name || "Cliente no informado"}</span>
          </div>
          <p className="mt-2 truncate text-lg font-bold text-slate-950">{event.name}</p>
          <p className="mt-1 flex items-center gap-2 text-sm text-slate-600">
            <CalendarClock className="h-4 w-4 text-emerald-700" />
            {formatDate(event.start_date)} - {formatDate(event.end_date)}
          </p>
        </div>
        <Link href={eventHref(event, role)}>
          <Button className="w-full md:w-auto" variant="secondary">
            <Eye className="h-4 w-4" />
            Abrir
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
