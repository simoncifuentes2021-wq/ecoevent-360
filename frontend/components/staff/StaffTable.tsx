"use client";

import { Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { RoleBadge } from "@/components/common/RoleBadge";
import { StaffRoleBadge } from "@/components/staff/StaffRoleBadge";
import { Button } from "@/components/ui/button";
import type { EventStaff } from "@/types/staff";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function StaffTable({ staff, loading, error, canManage, onRemove }: { staff: EventStaff[]; loading?: boolean; error?: string | null; canManage: boolean; onRemove: (item: EventStaff) => void }) {
  const columns: DataTableColumn<EventStaff>[] = [
    { key: "name", header: "Nombre", cell: (item) => <span className="font-semibold">{item.user?.full_name || item.user_id}</span> },
    { key: "email", header: "Email", cell: (item) => item.user?.email || "-" },
    { key: "role", header: "Rol global", cell: (item) => item.user?.role ? <RoleBadge role={item.user.role} /> : "-" },
    { key: "event_role", header: "Rol evento", cell: (item) => <StaffRoleBadge role={item.role_in_event} /> },
    { key: "start", header: "Inicio turno", cell: (item) => dateTime(item.shift_start) },
    { key: "end", header: "Fin turno", cell: (item) => dateTime(item.shift_end) }
  ];

  return (
    <DataTable
      actions={canManage ? (item) => <div className="flex justify-end"><Button size="sm" variant="ghost" onClick={() => onRemove(item)}><Trash2 className="h-4 w-4" /></Button></div> : undefined}
      columns={columns}
      data={staff}
      emptyDescription="Asigna supervisores y trabajadores para habilitar tareas operativas."
      emptyTitle="Sin personal asignado"
      error={error}
      getRowKey={(item) => item.user_id}
      loading={loading}
    />
  );
}
