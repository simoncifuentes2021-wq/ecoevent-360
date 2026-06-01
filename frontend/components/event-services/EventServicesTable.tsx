"use client";

import { Pencil, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { Button } from "@/components/ui/button";
import type { EventService } from "@/types/eventService";

type Props = {
  items: EventService[];
  loading?: boolean;
  error?: string | null;
  canManage: boolean;
  onEdit: (item: EventService) => void;
  onDelete: (item: EventService) => void;
};

function money(value: number | string | null | undefined) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}

export function EventServicesTable({ items, loading, error, canManage, onEdit, onDelete }: Props) {
  const columns: DataTableColumn<EventService>[] = [
    { key: "name", header: "Servicio", cell: (item) => <span className="font-semibold">{item.service?.name || item.service_id}</span> },
    { key: "category", header: "Categoria", cell: (item) => item.service?.category || "-" },
    { key: "quantity", header: "Cantidad", cell: (item) => item.quantity },
    { key: "unit", header: "Unidad", cell: (item) => item.service?.unit || "-" },
    { key: "unit_price", header: "Unitario", cell: (item) => money(item.unit_price) },
    { key: "total", header: "Total", cell: (item) => money(item.total_price ?? Number(item.quantity) * Number(item.unit_price || 0)) },
    { key: "notes", header: "Notas", cell: (item) => item.notes || "-" }
  ];

  return (
    <DataTable
      actions={
        canManage
          ? (item) => (
              <div className="flex justify-end gap-2">
                <Button size="sm" type="button" variant="secondary" onClick={() => onEdit(item)}>
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button size="sm" type="button" variant="ghost" onClick={() => onDelete(item)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            )
          : undefined
      }
      columns={columns}
      data={items}
      emptyDescription="Agrega servicios contratados para valorizar y controlar la operacion del evento."
      emptyTitle="Sin servicios contratados"
      error={error}
      getRowKey={(item) => item.id}
      loading={loading}
    />
  );
}
