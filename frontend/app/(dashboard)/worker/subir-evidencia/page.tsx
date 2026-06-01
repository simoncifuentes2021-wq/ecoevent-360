"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { MobileEvidenceForm } from "@/components/evidences/MobileEvidenceForm";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { MobileShell } from "@/components/worker/MobileShell";
import { ApiError } from "@/lib/api";
import { createEvidence } from "@/lib/api/evidences";
import { getEvents } from "@/lib/api/events";
import { getEventIncidents } from "@/lib/api/incidents";
import { getMyTasks } from "@/lib/api/tasks";
import type { Event } from "@/types/event";
import type { Incident } from "@/types/incident";
import type { Task } from "@/types/task";

export default function WorkerEvidencePage() {
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();
  const [events, setEvents] = useState<Event[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [eventId, setEventId] = useState(params.get("event_id") || "");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventData, taskData] = await Promise.all([getEvents({ page: 1, limit: 100 }), getMyTasks({ page: 1, limit: 100 })]);
      setEvents(eventData.items);
      setTasks(taskData.items);
      const selected = eventId || params.get("event_id") || eventData.items[0]?.id || taskData.items[0]?.event_id || "";
      setEventId(selected);
      if (selected) {
        const incidentData = await getEventIncidents(selected);
        setIncidents(incidentData.items);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId, params]);

  useEffect(() => { void load(); }, [load]);

  const eventTasks = useMemo(() => tasks.filter((task) => task.event_id === eventId), [eventId, tasks]);

  async function submit(formData: FormData) {
    const taskId = params.get("task_id");
    if (taskId && !formData.get("task_id")) formData.append("task_id", taskId);
    setSaving(true);
    try {
      await createEvidence(formData);
      toast({ tone: "success", title: "Evidencia subida" });
      router.push("/worker/mis-tareas");
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "No se pudo subir la evidencia.";
      toast({ tone: "error", title: "Error al subir", description: message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title="Subir evidencia" description="Adjunta una foto o PDF del trabajo realizado.">
        {loading ? <LoadingState label="Cargando datos..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && events.length === 0 ? <EmptyState title="Sin eventos" description="No tienes eventos disponibles para subir evidencia." /> : null}
        {events.length > 0 ? (
          <div className="space-y-4">
            <label className="grid gap-2 text-sm font-semibold">Evento<select className="h-12 rounded-2xl border px-4" value={eventId} onChange={(event) => setEventId(event.target.value)}>{events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            {eventId ? (
              <MobileEvidenceForm
                eventId={eventId}
                incidents={incidents}
                initialIncidentId={params.get("incident_id") || ""}
                initialTaskId={params.get("task_id") || ""}
                loading={saving}
                tasks={eventTasks}
                onCancel={() => router.push("/worker/mis-tareas")}
                onSubmit={submit}
              />
            ) : null}
          </div>
        ) : null}
      </MobileShell>
    </RoleGuard>
  );
}
