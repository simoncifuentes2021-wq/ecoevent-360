"use client";
import { useCallback, useEffect, useState } from "react"; import { Plus } from "lucide-react";
import { ErrorState } from "@/components/common/ErrorState"; import { Button } from "@/components/ui/button"; import { EnergyRecordFormModal } from "@/components/operations/EnergyRecordFormModal"; import { EnergyRecordTable } from "@/components/operations/EnergyRecordTable";
import { createEnergyRecord, getEnergyRecords } from "@/lib/api/energy"; import { getEventZones } from "@/lib/api/zones"; import type { EnergyRecord, EnergyRecordCreate } from "@/types/operations"; import type { Zone } from "@/types/zone";
export function EnergyRecordsTab({ eventId, canCreate }: { eventId: string; canCreate: boolean }) {
  const [records, setRecords] = useState<EnergyRecord[]>([]); const [zones, setZones] = useState<Zone[]>([]); const [error, setError] = useState<string | null>(null); const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false);
  const load = useCallback(async () => { try { const [r, z] = await Promise.all([getEnergyRecords(eventId), getEventZones(eventId)]); setRecords(r.items); setZones(z); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo cargar energia."); } }, [eventId]);
  useEffect(() => { void load(); }, [load]);
  async function submit(data: EnergyRecordCreate) { setSaving(true); try { await createEnergyRecord(eventId, data); setOpen(false); await load(); } finally { setSaving(false); } }
  return <div className="space-y-4"><div className="flex justify-between"><h3 className="font-bold">Energia</h3>{canCreate ? <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Registrar</Button> : null}</div>{error ? <ErrorState message={error} onRetry={load} /> : null}<EnergyRecordTable records={records} />{open ? <EnergyRecordFormModal loading={saving} zones={zones} onClose={() => setOpen(false)} onSubmit={submit} /> : null}</div>;
}
