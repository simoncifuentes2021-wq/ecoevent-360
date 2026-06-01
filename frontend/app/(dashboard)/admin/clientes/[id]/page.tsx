"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Edit } from "lucide-react";

import { ClientEventsTable } from "@/components/clients/ClientEventsTable";
import { ClientSummary } from "@/components/clients/ClientSummary";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { getClient, getClientEvents } from "@/lib/api/clients";
import { getEvents } from "@/lib/api/events";
import type { Client, ClientEvent } from "@/types/client";

export default function ClientDetailPage({ params }: { params: { id: string } }) {
  const [client, setClient] = useState<Client | null>(null);
  const [events, setEvents] = useState<ClientEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const clientData = await getClient(params.id);
      let clientEvents: ClientEvent[] = [];
      try {
        const eventsData = await getClientEvents(params.id, { page: 1, limit: 50 });
        clientEvents = eventsData.items;
      } catch {
        const eventsData = await getEvents({ client_id: params.id, page: 1, limit: 50 });
        clientEvents = eventsData.items.filter((event) => event.client_id === params.id);
      }
      setClient(clientData);
      setEvents(clientEvents);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el cliente.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <LoadingState label="Cargando cliente..." />;
  if (error || !client) return <ErrorState message={error || "Cliente no encontrado"} title="No pudimos cargar el cliente" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title={client.business_name}
          description="Detalle comercial, contacto y eventos asociados."
          actions={
            <div className="flex gap-2">
              <Link href="/admin/clientes">
                <Button variant="secondary">
                  <ArrowLeft className="h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <Link href={`/admin/clientes/${client.id}/editar`}>
                <Button>
                  <Edit className="h-4 w-4" />
                  Editar
                </Button>
              </Link>
            </div>
          }
        />
        <ClientSummary client={client} />
        <ClientEventsTable events={events} />
      </div>
    </RoleGuard>
  );
}
