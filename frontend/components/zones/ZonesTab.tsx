"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { ZoneCard } from "@/components/zones/ZoneCard";
import { ZoneFormModal } from "@/components/zones/ZoneFormModal";
import { ZoneTable } from "@/components/zones/ZoneTable";
import { Button } from "@/components/ui/button";
import { createEventZone, deleteZone, getEventZones, updateZone } from "@/lib/api/zones";
import { canManageZones } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";
import type { Zone, ZoneCreate, ZoneUpdate } from "@/types/zone";

export function ZonesTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formZone, setFormZone] = useState<Zone | null | undefined>();
  const [deleting, setDeleting] = useState<Zone | null>(null);
  const canManage = canManageZones(role);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setZones(await getEventZones(eventId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  async function save(data: ZoneCreate | ZoneUpdate) {
    setSaving(true);
    try {
      if (formZone) await updateZone(formZone.id, data);
      else await createEventZone(eventId, data as ZoneCreate);
      setFormZone(undefined);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteZone(deleting.id);
    setDeleting(null);
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Zonas del evento</h2>
          <p className="text-sm text-slate-600">Las zonas se usaran para tareas, incidencias, residuos y QR.</p>
        </div>
        {canManage ? <Button onClick={() => setFormZone(null)}><Plus className="h-4 w-4" />Crear zona</Button> : null}
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <div className="grid gap-3 md:hidden">
        {zones.map((zone) => <ZoneCard key={zone.id} canManage={canManage} zone={zone} onDelete={setDeleting} onEdit={setFormZone} />)}
      </div>
      <div className="hidden md:block">
        <ZoneTable canManage={canManage} error={null} loading={loading} zones={zones} onDelete={setDeleting} onEdit={setFormZone} />
      </div>
      {formZone !== undefined ? <ZoneFormModal loading={saving} zone={formZone} onClose={() => setFormZone(undefined)} onSubmit={save} /> : null}
      <ConfirmDialog open={Boolean(deleting)} title="Eliminar zona" description="Solo se eliminara si no tiene datos asociados." onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
    </div>
  );
}
