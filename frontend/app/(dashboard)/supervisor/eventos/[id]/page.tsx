"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { EventHeader } from "@/components/events/EventHeader";
import { EventTabs } from "@/components/events/EventTabs";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { getEvent } from "@/lib/api/events";
import type { Event } from "@/types/event";

export default function SupervisorEventDetailPage({ params }: { params: { id: string } }) {
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvent(await getEvent(params.id));
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) setError("No tienes permiso para ver este evento.");
      else if (err instanceof ApiError && err.status === 404) setError("El evento no existe o no esta asignado a tu usuario.");
      else setError(err instanceof Error ? err.message : "No se pudo cargar el evento.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <LoadingState label="Cargando evento..." />;
  if (error || !event) return <ErrorState message={error || "Evento no encontrado"} title="No pudimos cargar el evento" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPERVISOR"]}>
      <div className="space-y-6">
        <PageHeader title="Operacion del evento" description="Gestion supervisora de zonas, personal y tareas." actions={<Link href="/supervisor/eventos"><Button variant="secondary"><ArrowLeft className="h-4 w-4" />Volver</Button></Link>} />
        <EventHeader event={event} />
        <EventTabs event={event} eventId={event.id} role="SUPERVISOR" variant="supervisor" />
      </div>
    </RoleGuard>
  );
}
