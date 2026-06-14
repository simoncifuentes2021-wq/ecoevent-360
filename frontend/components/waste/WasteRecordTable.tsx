"use client";

import { Eye, FileImage, Pencil, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import { WasteDestinationBadge } from "@/components/waste/WasteDestinationBadge";
import { WasteTypeBadge } from "@/components/waste/WasteTypeBadge";
import type { WasteRecord, WasteType } from "@/types/waste";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

function typeLabel(record: WasteRecord, types: WasteType[]) {
  if (typeof record.waste_type === "object" && record.waste_type && "name" in record.waste_type) return record.waste_type.name;
  return types.find((item) => item.id === record.waste_type_id)?.name || String(record.waste_type || record.waste_type_id || "OTHER");
}

function recorderLabel(record: WasteRecord) {
  return record.recorder?.full_name || record.recorder?.email || (record.recorded_by ? "Usuario registrado" : "-");
}

export function WasteRecordTable({ records, wasteTypes, loading, error, canEdit, canDelete, onView, onEdit, onDelete }: { records: WasteRecord[]; wasteTypes: WasteType[]; loading?: boolean; error?: string | null; canEdit: boolean; canDelete: boolean; onView: (record: WasteRecord) => void; onEdit: (record: WasteRecord) => void; onDelete: (record: WasteRecord) => void }) {
  const columns: DataTableColumn<WasteRecord>[] = [
    { key: "date", header: "Fecha", cell: (record) => date(record.recorded_at || record.created_at) },
    { key: "zone", header: "Zona", cell: (record) => record.zone?.name || "-" },
    { key: "type", header: "Tipo", cell: (record) => <WasteTypeBadge value={typeLabel(record, wasteTypes)} /> },
    { key: "weight", header: "Peso kg", cell: (record) => `${Number(record.weight_kg || 0).toLocaleString("es-CL")} kg` },
    { key: "destination", header: "Destino", cell: (record) => <WasteDestinationBadge destination={record.destination} /> },
    { key: "evidence", header: "Evidencia", cell: (record) => record.evidence_id ? <FileImage className="h-4 w-4 text-emerald-700" /> : "-" },
    { key: "recorder", header: "Registrado por", cell: (record) => recorderLabel(record) }
  ];

  return (
    <DataTable
      actions={(record) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => onView(record)}><Eye className="h-4 w-4" /></Button>
          {canEdit ? <Button size="sm" variant="secondary" onClick={() => onEdit(record)}><Pencil className="h-4 w-4" /></Button> : null}
          {canDelete ? <Button size="sm" variant="ghost" onClick={() => onDelete(record)}><Trash2 className="h-4 w-4" /></Button> : null}
        </div>
      )}
      columns={columns}
      data={records}
      emptyDescription="Registra residuos por zona, tipo, peso, destino y evidencia."
      emptyTitle="Sin registros de residuos"
      error={error}
      getRowKey={(record) => record.id}
      loading={loading}
    />
  );
}
