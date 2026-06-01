"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarClock, Edit } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { EventHeader } from "@/components/events/EventHeader";
import { EventTabs } from "@/components/events/EventTabs";
import { StatusChangeDialog } from "@/components/events/StatusChangeDialog";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { changeEventStatus, getEvent } from "@/lib/api/events";
import type { Event, EventStatus } from "@/types/event";

export default function EventDetailPage({ params }: { params: { id: string } }) {
  const { user } = useAuth();
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvent(await getEvent(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el evento.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function updateStatus(status: EventStatus) {
    setStatusLoading(true);
    try {
      await changeEventStatus(params.id, status);
      setStatusOpen(false);
      await load();
    } finally {
      setStatusLoading(false);
    }
  }

  if (loading) return <LoadingState label="Cargando evento..." />;
  if (error || !event) return <ErrorState message={error || "Evento no encontrado"} title="No pudimos cargar el evento" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Detalle de evento"
          description="Centro operativo preparado para servicios, zonas, personal y tareas."
          actions={
            <div className="flex flex-wrap gap-2">
              <Link href="/admin/eventos">
                <Button variant="secondary">
                  <ArrowLeft className="h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <Button variant="secondary" onClick={() => setStatusOpen(true)}>
                <CalendarClock className="h-4 w-4" />
                Estado
              </Button>
              <Link href={`/admin/eventos/${event.id}/editar`}>
                <Button>
                  <Edit className="h-4 w-4" />
                  Editar
                </Button>
              </Link>
            </div>
          }
        />
        <EventHeader event={event} />
        <EventTabs eventId={event.id} role={user?.role} />
        <StatusChangeDialog event={statusOpen ? event : null} loading={statusLoading} onClose={() => setStatusOpen(false)} onConfirm={updateStatus} />
      </div>
    </RoleGuard>
  );
}
