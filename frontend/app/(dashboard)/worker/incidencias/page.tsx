"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Camera, ChevronRight, Plus, ShieldAlert } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { IncidentStatusBadge } from "@/components/incidents/IncidentStatusBadge";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { getEvents } from "@/lib/api/events";
import { getEventIncidents } from "@/lib/api/incidents";
import type { Incident } from "@/types/incident";

type WorkerIncident = Incident & {
  event_name?: string;
};

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin fecha";
}

export default function WorkerIncidentsPage() {
  const [incidents, setIncidents] = useState<WorkerIncident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const eventResponse = await getEvents({ page: 1, limit: 100 });
      const incidentResponses = await Promise.all(
        eventResponse.items.map(async (event) => {
          const response = await getEventIncidents(event.id, { page: 1, limit: 50 }).catch(() => ({ items: [] as Incident[] }));
          return response.items.map((incident) => ({ ...incident, event_name: event.name }));
        })
      );
      setIncidents(incidentResponses.flat());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar tus incidencias.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const openIncidents = useMemo(
    () => incidents.filter((incident) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(incident.status)),
    [incidents]
  );

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title="Incidencias" description="Revisa problemas reportados en tus eventos asignados.">
        <Link href="/worker/reportar-incidencia">
          <Button className="h-12 w-full">
            <Plus className="h-5 w-5" />
            Reportar incidencia
          </Button>
        </Link>

        <section className="rounded-3xl border bg-white p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-500">Abiertas</p>
              <p className="text-3xl font-black text-slate-950">{openIncidents.length}</p>
            </div>
            <ShieldAlert className="h-9 w-9 text-emerald-700" />
          </div>
        </section>

        {loading ? <LoadingState label="Cargando incidencias..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && !error && incidents.length === 0 ? (
          <EmptyState title="Sin incidencias" description="Cuando reportes o te asignen una incidencia, aparecera aqui." />
        ) : null}

        <div className="space-y-3">
          {incidents.map((incident) => (
            <article className="rounded-3xl border bg-white p-5 shadow-sm" key={incident.id}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-lg font-bold text-slate-950">{incident.title}</p>
                  <p className="mt-1 text-sm text-slate-600">{incident.event_name || "Evento asignado"}</p>
                </div>
                <PriorityBadge priority={incident.priority} />
              </div>

              <div className="mt-3 flex flex-wrap gap-2">
                <IncidentStatusBadge status={incident.status} />
              </div>

              <p className="mt-3 line-clamp-2 text-sm text-slate-700">{incident.description}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {incident.zone?.name || "Sin zona"} - {dateTime(incident.created_at)}
              </p>

              <div className="mt-4 grid grid-cols-2 gap-2">
                <Link href={`/worker/incidencias/${incident.id}`}>
                  <Button className="w-full" variant="secondary">
                    Ver detalle <ChevronRight className="h-4 w-4" />
                  </Button>
                </Link>
                <Link href={`/worker/subir-evidencia?event_id=${incident.event_id}&incident_id=${incident.id}`}>
                  <Button className="w-full" variant="ghost">
                    <Camera className="h-4 w-4" />
                    Evidencia
                  </Button>
                </Link>
              </div>
            </article>
          ))}
        </div>
      </MobileShell>
    </RoleGuard>
  );
}
