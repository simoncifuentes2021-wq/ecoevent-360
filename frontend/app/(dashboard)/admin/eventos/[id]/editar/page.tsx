"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { EventForm } from "@/components/events/EventForm";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { getClients } from "@/lib/api/clients";
import { deleteEvent, getEvent, updateEvent } from "@/lib/api/events";
import type { Client } from "@/types/client";
import type { Event, EventCreate, EventUpdate } from "@/types/event";

export default function EditEventPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [event, setEvent] = useState<Event | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventData, clientData] = await Promise.all([getEvent(params.id), getClients({ is_active: "true", page: 1, limit: 100 })]);
      setEvent(eventData);
      setClients(clientData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el evento.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: EventCreate | EventUpdate) {
    await updateEvent(params.id, data as EventUpdate);
    router.push(`/admin/eventos/${params.id}`);
  }

  async function cancelEvent() {
    await deleteEvent(params.id);
    router.push(`/admin/eventos/${params.id}`);
  }

  if (loading) return <LoadingState label="Cargando evento..." />;
  if (error || !event) return <ErrorState message={error || "Evento no encontrado"} title="No pudimos cargar el evento" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Editar evento"
          description={event.name}
          actions={
            event.status !== "CANCELLED" ? (
              <Button variant="secondary" onClick={() => setConfirmOpen(true)}>
                Cancelar evento
              </Button>
            ) : null
          }
        />
        <EventForm cancelHref={`/admin/eventos/${params.id}`} clients={clients} event={event} submitLabel="Guardar cambios" onSubmit={submit} />
        <ConfirmDialog
          description="El evento se marcara como cancelado sin eliminar su historial operativo."
          open={confirmOpen}
          title="Cancelar evento"
          onClose={() => setConfirmOpen(false)}
          onConfirm={cancelEvent}
        />
      </div>
    </RoleGuard>
  );
}
