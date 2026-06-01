"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Plus } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { createAlert, getEventAlerts, resolveAlert } from "@/lib/api/alerts";
import { getEventZones } from "@/lib/api/zones";
import type { Alert, AlertCreate } from "@/types/alert";
import type { UserRole } from "@/types/roles";
import type { Zone } from "@/types/zone";

function canManage(role?: UserRole | null) {
  return role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
}

export function AlertsTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<AlertCreate["priority"]>("MEDIUM");
  const [zoneId, setZoneId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setUnavailable(false);
    try {
      const [alertData, zoneData] = await Promise.all([getEventAlerts(eventId), getEventZones(eventId).catch(() => [])]);
      setAlerts(alertData.items);
      setZones(zoneData);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setUnavailable(true);
        setAlerts([]);
      } else {
        setError(err instanceof Error ? err.message : "No se pudieron cargar las alertas.");
      }
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void load();
  }, [load]);

  const openAlerts = useMemo(() => alerts.filter((alert) => !["RESOLVED", "CLOSED", "CANCELLED"].includes(alert.status)), [alerts]);

  async function submit() {
    if (!title.trim()) {
      setError("El titulo de la alerta es obligatorio.");
      return;
    }
    setSaving(true);
    try {
      await createAlert(eventId, {
        title: title.trim(),
        description: description.trim() || null,
        priority,
        zone_id: zoneId || null
      });
      setFormOpen(false);
      setTitle("");
      setDescription("");
      setPriority("MEDIUM");
      setZoneId("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo crear la alerta.");
    } finally {
      setSaving(false);
    }
  }

  async function markResolved(alert: Alert) {
    setSaving(true);
    try {
      await resolveAlert(alert.id, {});
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo resolver la alerta.");
    } finally {
      setSaving(false);
    }
  }

  if (unavailable) {
    return (
      <div className="rounded-3xl border bg-white p-6 shadow-sm">
        <EmptyState
          icon={<AlertTriangle className="h-10 w-10" />}
          title="Alertas no disponibles"
          description="El modulo de alertas aun no esta disponible en el backend. La pantalla queda preparada para activarlo cuando exista el endpoint."
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Alertas</h2>
          <p className="text-sm text-slate-600">Avisos operativos, riesgos y situaciones que requieren atencion.</p>
        </div>
        {canManage(role) ? <Button onClick={() => setFormOpen(true)}><Plus className="h-4 w-4" />Crear alerta</Button> : null}
      </div>

      {loading ? <LoadingState label="Cargando alertas..." /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && alerts.length === 0 ? <EmptyState title="Sin alertas" description="No hay alertas operativas para este evento." /> : null}

      <div className="grid gap-3 lg:grid-cols-2">
        {openAlerts.map((alert) => (
          <article className="rounded-3xl border bg-white p-5 shadow-sm" key={alert.id}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-lg font-bold text-slate-950">{alert.title}</p>
                <p className="mt-1 text-sm text-slate-600">{alert.zone?.name || "Sin zona"} - {alert.priority || "MEDIUM"}</p>
              </div>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-bold text-amber-700">{alert.status}</span>
            </div>
            {alert.description ? <p className="mt-3 text-sm text-slate-700">{alert.description}</p> : null}
            {canManage(role) ? (
              <Button className="mt-4" disabled={saving} variant="secondary" onClick={() => markResolved(alert)}>
                <CheckCircle2 className="h-4 w-4" />
                Resolver
              </Button>
            ) : null}
          </article>
        ))}
      </div>

      {formOpen ? (
        <ModalShell title="Crear alerta" description="Registra un aviso operativo para seguimiento del evento." onClose={() => setFormOpen(false)}>
          <div className="space-y-4">
            <label className="grid gap-2 text-sm font-semibold">Titulo<Input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
            <label className="grid gap-2 text-sm font-semibold">
              Zona
              <select className="h-10 rounded-md border px-3 text-sm" value={zoneId} onChange={(event) => setZoneId(event.target.value)}>
                <option value="">Sin zona</option>
                {zones.map((zone) => <option key={zone.id} value={zone.id}>{zone.name}</option>)}
              </select>
            </label>
            <label className="grid gap-2 text-sm font-semibold">
              Prioridad
              <select className="h-10 rounded-md border px-3 text-sm" value={priority} onChange={(event) => setPriority(event.target.value as AlertCreate["priority"])}>
                <option value="LOW">Baja</option>
                <option value="MEDIUM">Media</option>
                <option value="HIGH">Alta</option>
                <option value="CRITICAL">Critica</option>
              </select>
            </label>
            <label className="grid gap-2 text-sm font-semibold">
              Descripcion
              <textarea className="min-h-28 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={description} onChange={(event) => setDescription(event.target.value)} />
            </label>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setFormOpen(false)}>Cancelar</Button>
              <Button disabled={saving} onClick={submit}>{saving ? "Guardando..." : "Crear alerta"}</Button>
            </div>
          </div>
        </ModalShell>
      ) : null}
    </div>
  );
}
