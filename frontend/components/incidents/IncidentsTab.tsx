"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";
import { CloseIncidentDialog } from "@/components/incidents/CloseIncidentDialog";
import { IncidentDetailDrawer } from "@/components/incidents/IncidentDetailDrawer";
import { IncidentFormModal } from "@/components/incidents/IncidentFormModal";
import { IncidentTable } from "@/components/incidents/IncidentTable";
import { ResolveIncidentDialog } from "@/components/incidents/ResolveIncidentDialog";
import { Button } from "@/components/ui/button";
import { getEventEvidences } from "@/lib/api/evidences";
import { closeIncident, createIncident, getEventIncidents, resolveIncident, updateIncident } from "@/lib/api/incidents";
import { getEventStaff } from "@/lib/api/staff";
import { getEventZones } from "@/lib/api/zones";
import { canCloseIncident, canCreateIncident, canEditIncident, canResolveIncident } from "@/lib/permissions";
import type { Evidence } from "@/types/evidence";
import type { Incident, IncidentCreate, IncidentStatus, IncidentUpdate } from "@/types/incident";
import type { UserRole } from "@/types/roles";
import type { EventStaff } from "@/types/staff";
import type { Zone } from "@/types/zone";

export function IncidentsTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formIncident, setFormIncident] = useState<Incident | null | undefined>();
  const [detail, setDetail] = useState<Incident | null>(null);
  const [resolveTarget, setResolveTarget] = useState<Incident | null>(null);
  const [closeTarget, setCloseTarget] = useState<Incident | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [type, setType] = useState("");
  const [priority, setPriority] = useState("");
  const [zoneId, setZoneId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [incidentData, zoneData, staffData, evidenceData] = await Promise.all([getEventIncidents(eventId), getEventZones(eventId), getEventStaff(eventId), getEventEvidences(eventId)]);
      setIncidents(incidentData.items);
      setZones(zoneData);
      setStaff(staffData);
      setEvidences(evidenceData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => incidents.filter((item) => {
    const itemType = item.incident_type || item.type || "OTHER";
    return (!q || `${item.title} ${item.description}`.toLowerCase().includes(q.toLowerCase()))
      && (!status || item.status === status)
      && (!type || itemType === type)
      && (!priority || item.priority === priority)
      && (!zoneId || item.zone_id === zoneId);
  }), [incidents, priority, q, status, type, zoneId]);

  async function save(data: IncidentCreate | IncidentUpdate) {
    setSaving(true);
    try {
      if (formIncident) await updateIncident(formIncident.id, data as IncidentUpdate);
      else await createIncident(eventId, data as IncidentCreate);
      setFormIncident(undefined);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function doResolve(data: { solution: string; evidence_id?: string | null }) {
    if (!resolveTarget) return;
    setSaving(true);
    try {
      await resolveIncident(resolveTarget.id, data);
      setResolveTarget(null);
      setDetail(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function doClose() {
    if (!closeTarget) return;
    await closeIncident(closeTarget.id);
    setCloseTarget(null);
    setDetail(null);
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div><h2 className="text-xl font-bold text-slate-950">Incidencias</h2><p className="text-sm text-slate-600">Registra, asigna y resuelve situaciones operativas del evento.</p></div>
        {canCreateIncident(role) ? <Button onClick={() => setFormIncident(null)}><Plus className="h-4 w-4" />Crear incidencia</Button> : null}
      </div>
      <div className="grid gap-3 lg:grid-cols-[1fr_160px_160px_160px_180px]">
        <SearchInput placeholder="Buscar incidencia..." value={q} onChange={setQ} />
        <FilterSelect label="Estado" value={status} onChange={setStatus} options={[{ label: "Todos", value: "" }, { label: "Reportada", value: "REPORTED" }, { label: "Asignada", value: "ASSIGNED" }, { label: "En progreso", value: "IN_PROGRESS" }, { label: "Resuelta", value: "RESOLVED" }, { label: "Cerrada", value: "CLOSED" }]} />
        <FilterSelect label="Tipo" value={type} onChange={setType} options={[{ label: "Todos", value: "" }, { label: "Sanitaria", value: "SANITARY" }, { label: "Residuos", value: "WASTE" }, { label: "Limpieza", value: "CLEANING" }, { label: "Ambiental", value: "ENVIRONMENTAL" }, { label: "Seguridad", value: "SAFETY" }, { label: "Otra", value: "OTHER" }]} />
        <FilterSelect label="Prioridad" value={priority} onChange={setPriority} options={[{ label: "Todas", value: "" }, { label: "Baja", value: "LOW" }, { label: "Media", value: "MEDIUM" }, { label: "Alta", value: "HIGH" }, { label: "Critica", value: "CRITICAL" }]} />
        <FilterSelect label="Zona" value={zoneId} onChange={setZoneId} options={[{ label: "Todas", value: "" }, ...zones.map((zone) => ({ label: zone.name, value: zone.id }))]} />
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <IncidentTable canClose={canCloseIncident(role)} canEdit={canEditIncident(role)} canResolve={canResolveIncident(role)} error={null} incidents={filtered} loading={loading} onCloseIncident={setCloseTarget} onEdit={setFormIncident} onResolve={setResolveTarget} onView={setDetail} />
      {formIncident !== undefined ? <IncidentFormModal incident={formIncident} loading={saving} staff={staff} zones={zones} onClose={() => setFormIncident(undefined)} onSubmit={save} /> : null}
      {detail ? <IncidentDetailDrawer canClose={canCloseIncident(role)} canResolve={canResolveIncident(role)} incident={detail} onClose={() => setDetail(null)} onCloseIncident={() => setCloseTarget(detail)} onResolve={() => setResolveTarget(detail)} /> : null}
      {resolveTarget ? <ResolveIncidentDialog evidences={evidences} loading={saving} onClose={() => setResolveTarget(null)} onConfirm={doResolve} /> : null}
      <CloseIncidentDialog open={Boolean(closeTarget)} onClose={() => setCloseTarget(null)} onConfirm={doClose} />
    </div>
  );
}
