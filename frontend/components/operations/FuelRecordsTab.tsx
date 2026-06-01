"use client";
import { useCallback, useEffect, useState } from "react"; import { Plus } from "lucide-react";
import { ErrorState } from "@/components/common/ErrorState"; import { Button } from "@/components/ui/button"; import { FuelRecordFormModal } from "@/components/operations/FuelRecordFormModal"; import { FuelRecordTable } from "@/components/operations/FuelRecordTable";
import { createFuelRecord, getFuelRecords } from "@/lib/api/fuel"; import { getEventZones } from "@/lib/api/zones"; import type { FuelRecord, FuelRecordCreate } from "@/types/operations"; import type { Zone } from "@/types/zone";
export function FuelRecordsTab({ eventId, canCreate }: { eventId: string; canCreate: boolean }) {
  const [records, setRecords] = useState<FuelRecord[]>([]); const [zones, setZones] = useState<Zone[]>([]); const [error, setError] = useState<string | null>(null); const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false);
  const load = useCallback(async () => { try { const [r, z] = await Promise.all([getFuelRecords(eventId), getEventZones(eventId)]); setRecords(r.items); setZones(z); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo cargar combustible."); } }, [eventId]);
  useEffect(() => { void load(); }, [load]);
  async function submit(data: FuelRecordCreate) { setSaving(true); try { await createFuelRecord(eventId, data); setOpen(false); await load(); } finally { setSaving(false); } }
  return <div className="space-y-4"><div className="flex justify-between"><h3 className="font-bold">Combustible</h3>{canCreate ? <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Registrar</Button> : null}</div>{error ? <ErrorState message={error} onRetry={load} /> : null}<FuelRecordTable records={records} />{open ? <FuelRecordFormModal loading={saving} zones={zones} onClose={() => setOpen(false)} onSubmit={submit} /> : null}</div>;
}
