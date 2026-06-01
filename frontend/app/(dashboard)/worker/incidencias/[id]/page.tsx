"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarClock, MapPin, ShieldAlert } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { IncidentStatusBadge } from "@/components/incidents/IncidentStatusBadge";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { getIncident } from "@/lib/api/incidents";
import type { Incident } from "@/types/incident";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin fecha";
}

export default function WorkerIncidentDetailPage({ params }: { params: { id: string } }) {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setIncident(await getIncident(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la incidencia.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <LoadingState label="Cargando incidencia..." />;
  if (error || !incident) return <ErrorState title="No pudimos cargar la incidencia" message={error || "Incidencia no encontrada"} onRetry={load} />;

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title={incident.title} description="Detalle de la incidencia reportada.">
        <Link href="/worker/dashboard">
          <Button className="w-full" variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Volver al inicio
          </Button>
        </Link>

        <div className="rounded-3xl border bg-white p-5 shadow-sm">
          <div className="flex flex-wrap gap-2">
            <IncidentStatusBadge status={incident.status} />
            <PriorityBadge priority={incident.priority} />
          </div>

          <p className="mt-4 text-sm leading-6 text-slate-700">{incident.description}</p>

          <div className="mt-5 grid gap-3 text-sm text-slate-700">
            <p className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-emerald-700" />
              {incident.zone?.name || "Sin zona"}
            </p>
            <p className="flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-emerald-700" />
              {dateTime(incident.created_at)}
            </p>
            <p className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-emerald-700" />
              {incident.incident_type || incident.type || "OTRA"}
            </p>
          </div>
        </div>
      </MobileShell>
    </RoleGuard>
  );
}

