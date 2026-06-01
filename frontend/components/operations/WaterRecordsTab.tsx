"use client";
import { useCallback, useEffect, useState } from "react"; import { Plus } from "lucide-react";
import { ErrorState } from "@/components/common/ErrorState"; import { Button } from "@/components/ui/button"; import { WaterRecordFormModal } from "@/components/operations/WaterRecordFormModal"; import { WaterRecordTable } from "@/components/operations/WaterRecordTable";
import { createWaterRecord, getWaterRecords } from "@/lib/api/water"; import { getEventZones } from "@/lib/api/zones"; import type { WaterRecord, WaterRecordCreate } from "@/types/operations"; import type { Zone } from "@/types/zone";
export function WaterRecordsTab({ eventId, canCreate }: { eventId: string; canCreate: boolean }) {
  const [records, setRecords] = useState<WaterRecord[]>([]); const [zones, setZones] = useState<Zone[]>([]); const [error, setError] = useState<string | null>(null); const [open, setOpen] = useState(false); const [saving, setSaving] = useState(false);
  const load = useCallback(async () => { try { const [r, z] = await Promise.all([getWaterRecords(eventId), getEventZones(eventId)]); setRecords(r.items); setZones(z); } catch (e) { setError(e instanceof Error ? e.message : "No se pudo cargar agua."); } }, [eventId]);
  useEffect(() => { void load(); }, [load]);
  async function submit(data: WaterRecordCreate) { setSaving(true); try { await createWaterRecord(eventId, data); setOpen(false); await load(); } finally { setSaving(false); } }
  return <div className="space-y-4"><div className="flex justify-between"><h3 className="font-bold">Agua</h3>{canCreate ? <Button onClick={() => setOpen(true)}><Plus className="h-4 w-4" />Registrar</Button> : null}</div>{error ? <ErrorState message={error} onRetry={load} /> : null}<WaterRecordTable records={records} />{open ? <WaterRecordFormModal loading={saving} zones={zones} onClose={() => setOpen(false)} onSubmit={submit} /> : null}</div>;
}
