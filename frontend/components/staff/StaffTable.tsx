"use client";

import { CalendarCheck2, CircleAlert, Clock3, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { RoleBadge } from "@/components/common/RoleBadge";
import { StaffRoleBadge } from "@/components/staff/StaffRoleBadge";
import { Button } from "@/components/ui/button";
import type { EventStaff } from "@/types/staff";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

function invitationState(item: EventStaff) {
  const status = item.calendar_invitation_status || "PENDING";
  const styles = {
    SENT: "bg-emerald-50 text-emerald-800",
    ERROR: "bg-rose-50 text-rose-800",
    CANCELLED: "bg-slate-100 text-slate-600",
    PENDING: "bg-amber-50 text-amber-800"
  }[status];
  const labels = { SENT: "Invitación enviada", ERROR: "Error de envío", CANCELLED: "Invitación cancelada", PENDING: "Pendiente" };
  const Icon = status === "SENT" ? CalendarCheck2 : status === "ERROR" ? CircleAlert : Clock3;
  return <div className="max-w-64 space-y-1" title={item.calendar_invitation_error || undefined}>
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${styles}`}><Icon className="h-3.5 w-3.5" />{labels[status]}</span>
    {item.calendar_invitation_error ? <p className="text-xs leading-4 text-rose-700">{item.calendar_invitation_error}</p> : null}
    {status === "SENT" && item.calendar_invitation_sent_at ? <p className="text-xs text-muted-foreground">{dateTime(item.calendar_invitation_sent_at)}</p> : null}
  </div>;
}

export function StaffTable({ staff, loading, error, canManage, canRemove, onRemove }: { staff: EventStaff[]; loading?: boolean; error?: string | null; canManage: boolean; canRemove?: (item: EventStaff) => boolean; onRemove: (item: EventStaff) => void }) {
  const columns: DataTableColumn<EventStaff>[] = [
    { key: "name", header: "Nombre", cell: (item) => <span className="font-semibold">{item.user?.full_name || item.user_id}</span> },
    { key: "email", header: "Email", cell: (item) => item.user?.email || "-" },
    { key: "role", header: "Rol global", cell: (item) => item.user?.role ? <RoleBadge role={item.user.role} /> : "-" },
    { key: "event_role", header: "Rol evento", cell: (item) => <StaffRoleBadge role={item.role_in_event} /> },
    { key: "context", header: "Contexto", cell: (item) => <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold">{item.session_name || "General del evento"}</span> },
    { key: "start", header: "Inicio turno", cell: (item) => dateTime(item.shift_start) },
    { key: "end", header: "Fin turno", cell: (item) => dateTime(item.shift_end) },
    { key: "calendar_invitation", header: "Invitación calendario", cell: invitationState }
  ];

  return (
    <DataTable
      actions={canManage ? (item) => canRemove && !canRemove(item) ? null : <div className="flex justify-end"><Button size="sm" variant="ghost" onClick={() => onRemove(item)}><Trash2 className="h-4 w-4" /></Button></div> : undefined}
      columns={columns}
      data={staff}
      emptyDescription="Asigna supervisores y trabajadores para habilitar tareas operativas."
      emptyTitle="Sin personal asignado"
      error={error}
      getRowKey={(item) => item.show_assignment_id || `general-${item.user_id}`}
      loading={loading}
    />
  );
}
