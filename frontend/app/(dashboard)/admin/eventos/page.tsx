"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { EventFilters } from "@/components/events/EventFilters";
import { EventTable } from "@/components/events/EventTable";
import { StatusChangeDialog } from "@/components/events/StatusChangeDialog";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { getClients } from "@/lib/api/clients";
import { changeEventStatus, deleteEvent, getEvents } from "@/lib/api/events";
import type { Client } from "@/types/client";
import type { Event, EventStatus } from "@/types/event";

const limit = 20;

export default function AdminEventsPage() {
  const [events, setEvents] = useState<Event[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [clientId, setClientId] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [cancelTarget, setCancelTarget] = useState<Event | null>(null);
  const [statusTarget, setStatusTarget] = useState<Event | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const [eventData, clientData] = await Promise.all([
        getEvents({ q, status: status || undefined, client_id: clientId || undefined, page, limit }),
        getClients({ is_active: "true", page: 1, limit: 100 })
      ]);
      setEvents(eventData.items);
      setTotal(eventData.total);
      setClients(clientData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los eventos.");
    } finally {
      setLoading(false);
    }
  }, [q, status, clientId, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const visibleEvents = useMemo(() => {
    const clientsById = new Map(clients.map((client) => [client.id, client]));
    return events.map((event) => {
      if (event.client) return event;
      const client = clientsById.get(event.client_id);
      return client
        ? {
            ...event,
            client: {
              id: client.id,
              business_name: client.business_name,
              rut: client.rut,
              contact_email: client.contact_email
            }
          }
        : event;
    });
  }, [clients, events]);

  async function cancelEvent() {
    if (!cancelTarget) return;
    await deleteEvent(cancelTarget.id);
    setCancelTarget(null);
    await load();
  }

  async function updateStatus(nextStatus: EventStatus) {
    if (!statusTarget) return;
    setStatusLoading(true);
    try {
      await changeEventStatus(statusTarget.id, nextStatus);
      setStatusTarget(null);
      await load();
    } finally {
      setStatusLoading(false);
    }
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Eventos"
          description="Planifica y administra eventos, clientes, fechas y estado operativo."
          actions={
            <Link href="/admin/eventos/nuevo">
              <Button>
                <Plus className="h-4 w-4" />
                Crear evento
              </Button>
            </Link>
          }
        />
        <EventFilters
          clientId={clientId}
          clients={clients}
          q={q}
          status={status}
          onClientChange={(value) => {
            setClientId(value);
            setPage(1);
          }}
          onQChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          onStatusChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
        />
        <EventTable
          error={error}
          events={visibleEvents}
          limit={limit}
          loading={loading}
          page={page}
          total={total}
          onCancel={setCancelTarget}
          onChangeStatus={setStatusTarget}
          onPageChange={setPage}
        />
        <ConfirmDialog
          description={`El evento ${cancelTarget?.name || ""} se cancelara sin eliminar su historial.`}
          open={Boolean(cancelTarget)}
          title="Cancelar evento"
          onClose={() => setCancelTarget(null)}
          onConfirm={cancelEvent}
        />
        <StatusChangeDialog event={statusTarget} loading={statusLoading} onClose={() => setStatusTarget(null)} onConfirm={updateStatus} />
      </div>
    </RoleGuard>
  );
}
