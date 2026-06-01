"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { CalendarClock, ChevronRight, MapPin } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Input } from "@/components/ui/input";
import { MobileShell } from "@/components/worker/MobileShell";
import { getEvents } from "@/lib/api/events";
import type { Event } from "@/types/event";

function shortDate(value?: string | null) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value));
}

export default function WorkerEventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getEvents({ page: 1, limit: 100 });
      setEvents(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los eventos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return events;
    return events.filter((event) => event.name.toLowerCase().includes(term) || (event.city || "").toLowerCase().includes(term));
  }, [events, query]);

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title="Mis eventos" description="Revisa informaciÃ³n bÃ¡sica y zonas disponibles.">
        <Input placeholder="Buscar por nombre o ciudad..." value={query} onChange={(e) => setQuery(e.target.value)} />

        {loading ? <LoadingState label="Cargando eventos..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && !error && filtered.length === 0 ? (
          <EmptyState title="Sin eventos disponibles" description="No hay eventos asignados para tu usuario." />
        ) : null}

        <div className="space-y-2">
          {filtered.map((event) => (
            <Link
              className="flex items-center justify-between gap-3 rounded-3xl border bg-white p-4 shadow-sm hover:bg-emerald-50"
              href={`/worker/eventos/${event.id}`}
              key={event.id}
            >
              <div className="min-w-0">
                <p className="truncate font-semibold text-slate-950">{event.name}</p>
                <p className="mt-1 flex flex-wrap items-center gap-2 text-sm text-slate-600">
                  <span className="inline-flex items-center gap-1">
                    <CalendarClock className="h-4 w-4 text-emerald-700" />
                    {shortDate(event.start_date)}
                  </span>
                  {event.location_name || event.city ? (
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-4 w-4 text-emerald-700" />
                      {event.location_name || event.city}
                    </span>
                  ) : null}
                </p>
              </div>
              <ChevronRight className="h-5 w-5 text-slate-400" />
            </Link>
          ))}
        </div>
      </MobileShell>
    </RoleGuard>
  );
}

