"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { EmptyState } from "@/components/common/EmptyState";
import { WasteCharts } from "@/components/waste/WasteCharts";
import { WasteDeleteDialog } from "@/components/waste/WasteDeleteDialog";
import { CollectionPointsManager } from "@/components/waste/CollectionPointsManager";
import { WasteFilters } from "@/components/waste/WasteFilters";
import { WasteRecordDetailDrawer } from "@/components/waste/WasteRecordDetailDrawer";
import { WasteRecordFormModal } from "@/components/waste/WasteRecordFormModal";
import { WasteRecordTable } from "@/components/waste/WasteRecordTable";
import { WasteSummaryCards } from "@/components/waste/WasteSummaryCards";
import { WasteSummaryInsights } from "@/components/waste/WasteSummaryInsights";
import { Button } from "@/components/ui/button";
import { getEventEvidences } from "@/lib/api/evidences";
import { getUsers } from "@/lib/api/users";
import { createWasteRecord, deleteWasteRecord, getWasteRecords, getWasteSummary, updateWasteRecord } from "@/lib/api/waste";
import { getWasteTypes } from "@/lib/api/wasteTypes";
import { getEventZones } from "@/lib/api/zones";
import { normalizeWasteSummary } from "@/lib/normalizers/waste";
import { canCreateWasteRecord, canDeleteWasteRecord, canEditWasteRecord } from "@/lib/permissions";
import type { Evidence } from "@/types/evidence";
import type { UserRole } from "@/types/roles";
import type { User } from "@/types/user";
import type { WasteRecord, WasteRecordCreate, WasteRecordUpdate, WasteSummary, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";

function typeLabel(record: WasteRecord, types: WasteType[]) {
  if (typeof record.waste_type === "object" && record.waste_type && "name" in record.waste_type) return record.waste_type.name;
  return types.find((item) => item.id === record.waste_type_id)?.name || String(record.waste_type || record.waste_type_id || "OTHER");
}

function attachRecorders(records: WasteRecord[], users: User[]) {
  if (users.length === 0) return records;
  const usersById = new Map(users.map((user) => [user.id, user]));
  return records.map((record) => {
    if (record.recorder || !record.recorded_by) return record;
    const user = usersById.get(record.recorded_by);
    return user ? { ...record, recorder: { id: user.id, full_name: user.full_name, email: user.email } } : record;
  });
}

export function WasteTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [summary, setSummary] = useState<WasteSummary>(normalizeWasteSummary(null));
  const [records, setRecords] = useState<WasteRecord[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [wasteTypes, setWasteTypes] = useState<WasteType[]>([]);
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [formRecord, setFormRecord] = useState<WasteRecord | null | undefined>();
  const [detail, setDetail] = useState<WasteRecord | null>(null);
  const [deleting, setDeleting] = useState<WasteRecord | null>(null);
  const [q, setQ] = useState("");
  const [zoneId, setZoneId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [destination, setDestination] = useState("");
  const [activeTab, setActiveTab] = useState<"summary" | "environmental" | "collection">("summary");

  const loadSummary = useCallback(async () => {
    setSummaryLoading(true);
    setSummaryError(null);
    try {
      setSummary(normalizeWasteSummary(await getWasteSummary(eventId)));
    } catch {
      setSummaryError("No fue posible cargar el resumen ambiental.");
    } finally {
      setSummaryLoading(false);
    }
  }, [eventId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [, recordData, zoneData, evidenceData, typeData, userData] = await Promise.all([
        loadSummary(),
        getWasteRecords(eventId),
        getEventZones(eventId),
        getEventEvidences(eventId),
        getWasteTypes().catch(() => []),
        getUsers({ page: 1, limit: 100 }).then((response) => response.items).catch(() => [])
      ]);
      setRecords(attachRecorders(recordData.items, userData));
      setZones(zoneData);
      setEvidences(evidenceData.items);
      setWasteTypes(typeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el resumen de residuos.");
    } finally {
      setLoading(false);
    }
  }, [eventId, loadSummary]);

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

  const tabs = [
    { id: "summary" as const, label: "Resumen" },
    { id: "environmental" as const, label: "Registros ambientales" },
    ...(canEditWasteRecord(role) ? [{ id: "collection" as const, label: "Acopios" }] : []),
  ];
  const summaryContent = summaryError ? (
    <ErrorState title="Resumen ambiental no disponible" message={summaryError} onRetry={() => void loadSummary()} />
  ) : summaryLoading ? (
    <div className="space-y-4">
      <WasteSummaryCards loading summary={summary} />
      <WasteSummaryInsights loading summary={summary} />
      <WasteCharts byType={[]} bySource={[]} byCollectionPoint={[]} loading totalKg={0} />
    </div>
  ) : summary.records_count === 0 ? (
    <div className="space-y-4">
      <WasteSummaryCards summary={summary} />
      <WasteSummaryInsights summary={summary} />
      <EmptyState
        title="Aún no hay residuos registrados"
        description="Los registros de Acopios o ingresados directamente en EcoEvent aparecerán aquí."
        action={canCreateWasteRecord(role) ? <Button onClick={() => setFormRecord(null)}><Plus className="h-4 w-4" />Registrar residuo</Button> : undefined}
      />
    </div>
  ) : (
    <div className="space-y-4">
      <WasteSummaryCards summary={summary} />
      <WasteSummaryInsights summary={summary} />
      <WasteCharts byType={summary.by_type} bySource={summary.by_source} byCollectionPoint={summary.by_collection_point} totalKg={summary.total_event_kg} />
    </div>
  );

  return <div className="space-y-5">
    <div><h2 className="text-xl font-bold text-slate-950">Residuos y gestión ambiental</h2><p className="text-sm text-slate-600">Consulta la gestión ambiental y la recepción en acopios en secciones separadas.</p></div>
    <nav aria-label="Secciones de residuos" className="flex flex-wrap gap-2 border-b pb-3">{tabs.map(({ id, label }) => <button key={id} type="button" aria-selected={activeTab === id} onClick={() => setActiveTab(id)} className={`rounded-lg px-4 py-2 text-sm font-semibold ${activeTab === id ? "bg-emerald-700 text-white" : "border bg-white text-slate-700 hover:bg-slate-50"}`}>{label}</button>)}</nav>
    {error ? <ErrorState message={error} onRetry={load} /> : null}
    {activeTab === "summary" ? summaryContent : null}
    {activeTab === "environmental" ? <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="font-bold">Registros ambientales</h3><p className="text-sm text-slate-600">Destino, zona y evidencia del manejo final; estos datos alimentan el resumen ambiental.</p></div>{canCreateWasteRecord(role) ? <Button onClick={() => setFormRecord(null)}><Plus className="h-4 w-4" />Registrar residuo</Button> : null}</div>
      <WasteFilters destination={destination} q={q} typeId={typeId} wasteTypes={wasteTypes} zoneId={zoneId} zones={zones} onDestinationChange={setDestination} onQChange={setQ} onTypeChange={setTypeId} onZoneChange={setZoneId} />
      <WasteRecordTable canDelete={canDeleteWasteRecord(role)} canEdit={canEditWasteRecord(role)} error={null} loading={loading} records={filtered} wasteTypes={wasteTypes} onDelete={setDeleting} onEdit={setFormRecord} onView={setDetail} />
    </section> : null}
    {activeTab === "collection" ? <CollectionPointsManager eventId={eventId} canManage={canEditWasteRecord(role)} /> : null}
    {formRecord !== undefined ? <WasteRecordFormModal eventId={eventId} evidences={evidences} loading={saving} record={formRecord} wasteTypes={wasteTypes} zones={zones} onClose={() => setFormRecord(undefined)} onSubmit={save} /> : null}
    {detail ? <WasteRecordDetailDrawer canDelete={canDeleteWasteRecord(role)} canEdit={canEditWasteRecord(role)} record={detail} typeLabel={typeLabel(detail, wasteTypes)} onClose={() => setDetail(null)} onDelete={() => setDeleting(detail)} onEdit={() => setFormRecord(detail)} /> : null}
    <WasteDeleteDialog record={deleting} onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
  </div>;
}
