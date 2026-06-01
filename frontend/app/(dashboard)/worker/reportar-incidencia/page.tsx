"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { MobileIncidentForm } from "@/components/incidents/MobileIncidentForm";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { ApiError } from "@/lib/api";
import { createIncident } from "@/lib/api/incidents";
import { getEvents } from "@/lib/api/events";
import type { Event } from "@/types/event";
import type { IncidentCreate } from "@/types/incident";

export default function WorkerIncidentPage() {
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();
  const [events, setEvents] = useState<Event[]>([]);
  const [eventId, setEventId] = useState(params.get("event_id") || "");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getEvents({ page: 1, limit: 100 });
      setEvents(response.items);
      setEventId((current) => current || response.items[0]?.id || "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function submit(data: IncidentCreate) {
    if (!eventId) return;
    setSaving(true);
    try {
      await createIncident(eventId, data);
      toast({ tone: "success", title: "Incidencia reportada" });
      router.push("/worker/mis-tareas");
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "No se pudo reportar la incidencia.";
      toast({ tone: "error", title: "Error al reportar", description: message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title="Reportar incidencia" description="Registra rapidamente un problema en terreno.">
        {loading ? <LoadingState label="Cargando eventos..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && events.length === 0 ? <EmptyState title="Sin eventos" description="No tienes eventos disponibles para reportar." /> : null}
        {events.length > 0 ? (
          <div className="space-y-4">
            <label className="grid gap-2 text-sm font-semibold">Evento<select className="h-12 rounded-2xl border px-4" value={eventId} onChange={(event) => setEventId(event.target.value)}>{events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            {eventId ? <MobileIncidentForm eventId={eventId} loading={saving} onCancel={() => router.push("/worker/mis-tareas")} onSubmit={submit} /> : null}
            <Button disabled variant="secondary">Subir foto despues de crear</Button>
          </div>
        ) : null}
      </MobileShell>
    </RoleGuard>
  );
}
