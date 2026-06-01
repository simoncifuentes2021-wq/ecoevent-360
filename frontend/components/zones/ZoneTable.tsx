"use client";

import { Pencil, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import type { Zone } from "@/types/zone";

export function ZoneTable({ zones, loading, error, canManage, onEdit, onDelete }: { zones: Zone[]; loading?: boolean; error?: string | null; canManage: boolean; onEdit: (zone: Zone) => void; onDelete: (zone: Zone) => void }) {
  const columns: DataTableColumn<Zone>[] = [
    { key: "name", header: "Zona", cell: (zone) => <span className="font-semibold">{zone.name}</span> },
    { key: "description", header: "Descripcion", cell: (zone) => zone.description || "-" },
    { key: "qr", header: "QR", cell: (zone) => zone.qr_code_url ? "Preparado" : "Pendiente" }
  ];

  return (
    <DataTable
      actions={canManage ? (zone) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => onEdit(zone)}><Pencil className="h-4 w-4" /></Button>
          <Button size="sm" variant="ghost" onClick={() => onDelete(zone)}><Trash2 className="h-4 w-4" /></Button>
        </div>
      ) : undefined}
      columns={columns}
      data={zones}
      emptyDescription="Crea zonas para asignar tareas, incidencias, residuos y futuros QR."
      emptyTitle="Sin zonas"
      error={error}
      getRowKey={(zone) => zone.id}
      loading={loading}
    />
  );
}
