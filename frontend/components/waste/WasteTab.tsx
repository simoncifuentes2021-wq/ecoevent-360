"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { WasteCharts } from "@/components/waste/WasteCharts";
import { WasteDeleteDialog } from "@/components/waste/WasteDeleteDialog";
import { WasteFilters } from "@/components/waste/WasteFilters";
import { WasteRecordDetailDrawer } from "@/components/waste/WasteRecordDetailDrawer";
import { WasteRecordFormModal } from "@/components/waste/WasteRecordFormModal";
import { WasteRecordTable } from "@/components/waste/WasteRecordTable";
import { WasteSummaryCards } from "@/components/waste/WasteSummaryCards";
import { Button } from "@/components/ui/button";
import { getEventEvidences } from "@/lib/api/evidences";
import { createWasteRecord, deleteWasteRecord, getWasteRecords, getWasteSummary, updateWasteRecord } from "@/lib/api/waste";
import { getWasteTypes } from "@/lib/api/wasteTypes";
import { getEventZones } from "@/lib/api/zones";
import { normalizeWasteSummary } from "@/lib/normalizers/waste";
import { canCreateWasteRecord, canDeleteWasteRecord, canEditWasteRecord } from "@/lib/permissions";
import type { Evidence } from "@/types/evidence";
import type { UserRole } from "@/types/roles";
import type { WasteRecord, WasteRecordCreate, WasteRecordUpdate, WasteSummary, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";

function typeLabel(record: WasteRecord, types: WasteType[]) {
  if (typeof record.waste_type === "object" && record.waste_type && "name" in record.waste_type) return record.waste_type.name;
  return types.find((item) => item.id === record.waste_type_id)?.name || String(record.waste_type || record.waste_type_id || "OTHER");
}

export function WasteTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [summary, setSummary] = useState<WasteSummary>(normalizeWasteSummary(null));
  const [records, setRecords] = useState<WasteRecord[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [wasteTypes, setWasteTypes] = useState<WasteType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formRecord, setFormRecord] = useState<WasteRecord | null | undefined>();
  const [detail, setDetail] = useState<WasteRecord | null>(null);
  const [deleting, setDeleting] = useState<WasteRecord | null>(null);
  const [q, setQ] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [destination, setDestination] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [rawSummary, recordData, zoneData, evidenceData, typeData] = await Promise.all([
        getWasteSummary(eventId),
        getWasteRecords(eventId),
        getEventZones(eventId),
        getEventEvidences(eventId),
        getWasteTypes().catch(() => [])
      ]);
      setSummary(normalizeWasteSummary(rawSummary));
      setRecords(recordData.items);
      setZones(zoneData);
      setEvidences(evidenceData.items);
      setWasteTypes(typeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el resumen de residuos.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => records.filter((record) => {
    const label = typeLabel(record, wasteTypes);
    return (!q || `${record.notes || ""} ${record.destination_detail || ""} ${label}`.toLowerCase().includes(q.toLowerCase()))
      && (!zoneId || record.zone_id === zoneId)
      && (!typeId || record.waste_type_id === typeId || record.waste_type === typeId || label === typeId)
      && (!destination || record.destination === destination);
  }), [destination, q, records, typeId, wasteTypes, zoneId]);

  async function save(data: WasteRecordCreate | WasteRecordUpdate) {
    setSaving(true);
    try {
      if (formRecord) await updateWasteRecord(formRecord.id, data);
      else await createWasteRecord(eventId, data as WasteRecordCreate);
      setFormRecord(undefined);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteWasteRecord(deleting.id);
    setDeleting(null);
    setDetail(null);
    await load();
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div><h2 className="text-xl font-bold text-slate-950">Residuos y gestion ambiental</h2><p className="text-sm text-slate-600">Registra kg, tipo, destino, zona y evidencia para medir recuperacion.</p></div>
        {canCreateWasteRecord(role) ? <Button onClick={() => setFormRecord(null)}><Plus className="h-4 w-4" />Registrar residuo</Button> : null}
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <WasteSummaryCards summary={summary} />
      <WasteCharts byDestination={summary.by_destination} byType={summary.by_type} byZone={summary.by_zone} />
      <WasteFilters destination={destination} q={q} typeId={typeId} wasteTypes={wasteTypes} zoneId={zoneId} zones={zones} onDestinationChange={setDestination} onQChange={setQ} onTypeChange={setTypeId} onZoneChange={setZoneId} />
      <WasteRecordTable canDelete={canDeleteWasteRecord(role)} canEdit={canEditWasteRecord(role)} error={null} loading={loading} records={filtered} wasteTypes={wasteTypes} onDelete={setDeleting} onEdit={setFormRecord} onView={setDetail} />
      {formRecord !== undefined ? <WasteRecordFormModal evidences={evidences} loading={saving} record={formRecord} wasteTypes={wasteTypes} zones={zones} onClose={() => setFormRecord(undefined)} onSubmit={save} /> : null}
      {detail ? <WasteRecordDetailDrawer canDelete={canDeleteWasteRecord(role)} canEdit={canEditWasteRecord(role)} record={detail} typeLabel={typeLabel(detail, wasteTypes)} onClose={() => setDetail(null)} onDelete={() => setDeleting(detail)} onEdit={() => setFormRecord(detail)} /> : null}
      <WasteDeleteDialog record={deleting} onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
    </div>
  );
}
