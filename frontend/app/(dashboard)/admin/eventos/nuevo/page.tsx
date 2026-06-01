"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { EventForm } from "@/components/events/EventForm";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { getClients } from "@/lib/api/clients";
import { createEvent } from "@/lib/api/events";
import type { Client } from "@/types/client";
import type { EventCreate, EventUpdate } from "@/types/event";

export default function NewEventPage() {
  const router = useRouter();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getClients({ is_active: "true", page: 1, limit: 100 });
      setClients(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar clientes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: EventCreate | EventUpdate) {
    const event = await createEvent(data as EventCreate);
    router.push(`/admin/eventos/${event.id}`);
  }

  if (loading) return <LoadingState label="Cargando clientes..." />;
  if (error) return <ErrorState message={error} title="No pudimos preparar el formulario" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader title="Crear evento" description="Configura cliente, ubicacion, fechas y estado inicial." />
        <EventForm cancelHref="/admin/eventos" clients={clients} submitLabel="Crear evento" onSubmit={submit} />
      </div>
    </RoleGuard>
  );
}
