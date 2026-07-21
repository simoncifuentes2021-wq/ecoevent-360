"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Plus } from "lucide-react";

import { CarbonCharts } from "@/components/carbon/CarbonCharts";
import { CarbonDeleteDialog } from "@/components/carbon/CarbonDeleteDialog";
import { CarbonFilters } from "@/components/carbon/CarbonFilters";
import { CarbonRecordDetailDrawer } from "@/components/carbon/CarbonRecordDetailDrawer";
import { CarbonRecordFormModal } from "@/components/carbon/CarbonRecordFormModal";
import { CarbonRecordTable } from "@/components/carbon/CarbonRecordTable";
import { CarbonSummaryCards } from "@/components/carbon/CarbonSummaryCards";
import { ErrorState } from "@/components/common/ErrorState";
import { OperationalConsumptionTabs } from "@/components/operations/OperationalConsumptionTabs";
import { Button } from "@/components/ui/button";
import { getEventEvidences } from "@/lib/api/evidences";
import { createCarbonRecord, deleteCarbonRecord, getCarbonRecords, getCarbonSummary, updateCarbonRecord } from "@/lib/api/carbon";
import { getCarbonFactors } from "@/lib/api/carbonFactors";
import { normalizeCarbonSummary } from "@/lib/normalizers/carbon";
import { canCreateCarbonRecord, canDeleteCarbonRecord, canEditCarbonRecord } from "@/lib/permissions";
import type { CarbonFactor, CarbonRecord, CarbonRecordCreate, CarbonRecordUpdate, CarbonSummary } from "@/types/carbon";
import type { Evidence } from "@/types/evidence";
import type { UserRole } from "@/types/roles";

export function CarbonTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [summary, setSummary] = useState<CarbonSummary>(normalizeCarbonSummary(null));
  const [records, setRecords] = useState<CarbonRecord[]>([]);
  const [factors, setFactors] = useState<CarbonFactor[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formRecord, setFormRecord] = useState<CarbonRecord | null | undefined>();
  const [detail, setDetail] = useState<CarbonRecord | null>(null);
  const [deleting, setDeleting] = useState<CarbonRecord | null>(null);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [scope, setScope] = useState("");
  const [mode, setMode] = useState<"carbon" | "operations">("carbon");

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [rawSummary, recordData, factorData, evidenceData] = await Promise.all([getCarbonSummary(eventId), getCarbonRecords(eventId), getCarbonFactors({ page: 1, limit: 100 }).catch(() => ({ items: [] })), getEventEvidences(eventId)]);
      setSummary(normalizeCarbonSummary(rawSummary));
      setRecords(recordData.items);
      setFactors(factorData.items);
      setEvidences(evidenceData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el resumen de huella.");
    } finally { setLoading(false); }
  }, [eventId]);
  useEffect(() => { void load(); }, [load]);

  const filtered = useMemo(() => records.filter((record) => (!q || `${record.source || ""} ${record.description || ""} ${record.notes || ""}`.toLowerCase().includes(q.toLowerCase())) && (!category || record.category === category) && (!scope || record.scope === scope)), [category, q, records, scope]);
  async function save(data: CarbonRecordCreate | CarbonRecordUpdate) { setSaving(true); try { if (formRecord) await updateCarbonRecord(formRecord.id, data); else await createCarbonRecord(eventId, data as CarbonRecordCreate); setFormRecord(undefined); await load(); } finally { setSaving(false); } }
  async function confirmDelete() { if (!deleting) return; await deleteCarbonRecord(deleting.id); setDeleting(null); setDetail(null); await load(); }

  return <div className="space-y-5"><div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"><div><h2 className="text-xl font-bold text-slate-950">Huella de carbono</h2><p className="text-sm text-slate-600">Registra actividad, factores y consumos para visualizar CO2e.</p></div><div className="flex gap-2"><Button size="sm" variant={mode === "carbon" ? "primary" : "secondary"} onClick={() => setMode("carbon")}>Carbono</Button><Button size="sm" variant={mode === "operations" ? "primary" : "secondary"} onClick={() => setMode("operations")}>Consumos</Button>{mode === "carbon" && canCreateCarbonRecord(role) ? <Button onClick={() => setFormRecord(null)}><Plus className="h-4 w-4" />Agregar registro</Button> : null}</div></div>{error ? <ErrorState message={error} onRetry={load} /> : null}{mode === "operations" ? <OperationalConsumptionTabs eventId={eventId} role={role} /> : <><CarbonSummaryCards summary={summary} /><CarbonCharts byCategory={summary.by_category} byDate={summary.by_date} byScope={summary.by_scope} bySource={summary.by_source} /><CarbonFilters category={category} q={q} scope={scope} onCategoryChange={setCategory} onQChange={setQ} onScopeChange={setScope} /><CarbonRecordTable canDelete={canDeleteCarbonRecord(role)} canEdit={canEditCarbonRecord(role)} error={null} loading={loading} records={filtered} onDelete={setDeleting} onEdit={setFormRecord} onView={setDetail} /></>}{formRecord !== undefined ? <CarbonRecordFormModal evidences={evidences} factors={factors} loading={saving} record={formRecord} onClose={() => setFormRecord(undefined)} onSubmit={save} /> : null}{detail ? <CarbonRecordDetailDrawer canDelete={canDeleteCarbonRecord(role)} canEdit={canEditCarbonRecord(role)} record={detail} onClose={() => setDetail(null)} onDelete={() => setDeleting(detail)} onEdit={() => setFormRecord(detail)} /> : null}<CarbonDeleteDialog record={deleting} onClose={() => setDeleting(null)} onConfirm={confirmDelete} /></div>;
}
