"use client";

import { Pencil, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import type { WasteType } from "@/types/waste";

export function WasteTypeTable({ items, onEdit, onDelete }: { items: WasteType[]; onEdit: (item: WasteType) => void; onDelete: (item: WasteType) => void }) {
  const columns: DataTableColumn<WasteType>[] = [
    { key: "name", header: "Nombre", cell: (item) => <span className="font-semibold">{item.name}</span> },
    { key: "description", header: "Descripcion", cell: (item) => item.description || "-" },
    { key: "recyclable", header: "Reciclable", cell: (item) => <StatusBadge status={item.is_recyclable ? "ACTIVE" : "INACTIVE"} /> },
    { key: "created", header: "Creado", cell: (item) => item.created_at ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short" }).format(new Date(item.created_at)) : "-" }
  ];
  return <DataTable actions={(item) => <div className="flex justify-end gap-2"><Button size="sm" variant="secondary" onClick={() => onEdit(item)}><Pencil className="h-4 w-4" /></Button><Button size="sm" variant="ghost" onClick={() => onDelete(item)}><Trash2 className="h-4 w-4" /></Button></div>} columns={columns} data={items} emptyTitle="Sin tipos de residuos" emptyDescription="Crea tipos para clasificar registros ambientales." getRowKey={(item) => item.id} />;
}
