"use client";

import { Eye, FileImage, Pencil, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { CarbonCategoryBadge } from "@/components/carbon/CarbonCategoryBadge";
import { CarbonScopeBadge } from "@/components/carbon/CarbonScopeBadge";
import { formatKgCO2e } from "@/lib/normalizers/carbon";
import type { CarbonRecord } from "@/types/carbon";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}
export function recordKg(record: CarbonRecord) {
  return Number(record.kg_co2e ?? record.emissions_kgco2e ?? 0);
}
export function factorValue(record: CarbonRecord) {
  return Number(record.emission_factor_value ?? record.emission_factor?.factor_value ?? record.factor?.factor_value ?? record.factor?.factor_kgco2e ?? 0);
}

export function CarbonRecordTable({ records, loading, error, canEdit, canDelete, onView, onEdit, onDelete }: { records: CarbonRecord[]; loading?: boolean; error?: string | null; canEdit: boolean; canDelete: boolean; onView: (record: CarbonRecord) => void; onEdit: (record: CarbonRecord) => void; onDelete: (record: CarbonRecord) => void }) {
  const columns: DataTableColumn<CarbonRecord>[] = [
    { key: "date", header: "Fecha", cell: (r) => date(r.recorded_at || r.created_at) },
    { key: "category", header: "Categoria", cell: (r) => <CarbonCategoryBadge category={r.category} /> },
    { key: "scope", header: "Alcance", cell: (r) => <CarbonScopeBadge scope={r.scope} /> },
    { key: "source", header: "Fuente", cell: (r) => r.source || r.description || "-" },
    { key: "activity", header: "Actividad", cell: (r) => `${Number(r.activity_value || 0).toLocaleString("es-CL")} ${r.activity_unit}` },
    { key: "factor", header: "Factor", cell: (r) => factorValue(r).toLocaleString("es-CL", { maximumFractionDigits: 6 }) },
    { key: "co2", header: "kgCO2e", cell: (r) => formatKgCO2e(recordKg(r)) },
    { key: "evidence", header: "Evidencia", cell: (r) => r.evidence_id ? <FileImage className="h-4 w-4 text-emerald-700" /> : "-" }
  ];
  return <DataTable actions={(r) => <div className="flex justify-end gap-2"><Button size="sm" variant="secondary" onClick={() => onView(r)}><Eye className="h-4 w-4" /></Button>{canEdit ? <Button size="sm" variant="secondary" onClick={() => onEdit(r)}><Pencil className="h-4 w-4" /></Button> : null}{canDelete ? <Button size="sm" variant="ghost" onClick={() => onDelete(r)}><Trash2 className="h-4 w-4" /></Button> : null}</div>} columns={columns} data={records} emptyDescription="Agrega registros de actividad para calcular la huella del evento." emptyTitle="Sin registros de carbono" error={error} getRowKey={(r) => r.id} loading={loading} />;
}
