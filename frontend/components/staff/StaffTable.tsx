"use client";

import { CalendarCheck2, CircleAlert, Clock3, Mail, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { RoleBadge } from "@/components/common/RoleBadge";
import { StaffRoleBadge } from "@/components/staff/StaffRoleBadge";
import { Button } from "@/components/ui/button";
import type { EventStaff } from "@/types/staff";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

function invitationState(item: EventStaff) {
  const calendarStatus = item.calendar_invitation_status || "PENDING";
  const resendStatus = item.resend_invitation_status || "PENDING";
  const calendarLabel = {
    SENT: "Solicitud aceptada por Google",
    ERROR: "Error de Google Calendar",
    CANCELLED: "Invitación cancelada",
    PENDING: "Pendiente en Google Calendar"
  }[calendarStatus];
  const resendLabel = {
    ACCEPTED: "Correo aceptado por Resend",
    ERROR: "Error en correo directo",
    PENDING: "Correo directo pendiente"
  }[resendStatus];
  const calendarTone = calendarStatus === "SENT" ? "bg-emerald-50 text-emerald-800" : calendarStatus === "ERROR" ? "bg-rose-50 text-rose-800" : calendarStatus === "CANCELLED" ? "bg-slate-100 text-slate-600" : "bg-amber-50 text-amber-800";
  const resendTone = resendStatus === "ACCEPTED" ? "bg-emerald-50 text-emerald-800" : resendStatus === "ERROR" ? "bg-rose-50 text-rose-800" : "bg-amber-50 text-amber-800";
  const CalendarIcon = calendarStatus === "SENT" ? CalendarCheck2 : calendarStatus === "ERROR" ? CircleAlert : Clock3;
  const MailIcon = resendStatus === "ACCEPTED" ? Mail : resendStatus === "ERROR" ? CircleAlert : Clock3;
  return <div className="min-w-[260px] space-y-2">
    <div>
      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${calendarTone}`} title="Google aceptó registrar o actualizar el evento; esto no confirma la entrega de un correo."><CalendarIcon className="h-3.5 w-3.5" />{calendarLabel}</span>
      {item.calendar_invitation_error ? <p className="mt-1 text-xs leading-4 text-rose-700">{item.calendar_invitation_error}</p> : null}
      {calendarStatus === "SENT" && item.calendar_invitation_sent_at ? <p className="mt-1 text-xs text-muted-foreground">{dateTime(item.calendar_invitation_sent_at)}</p> : null}
    </div>
    <div>
      <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${resendTone}`} title="Resend aceptó la solicitud de correo; esto no confirma la entrega en la bandeja."><MailIcon className="h-3.5 w-3.5" />{resendLabel}</span>
      {item.resend_invitation_error ? <p className="mt-1 text-xs leading-4 text-rose-700">{item.resend_invitation_error}</p> : null}
      {resendStatus === "ACCEPTED" && item.resend_invitation_accepted_at ? <p className="mt-1 text-xs text-muted-foreground">{dateTime(item.resend_invitation_accepted_at)}</p> : null}
    </div>
  </div>;
}

export function StaffTable({ staff, loading, error, canManage, canRemove, onRemove }: { staff: EventStaff[]; loading?: boolean; error?: string | null; canManage: boolean; canRemove?: (item: EventStaff) => boolean; onRemove: (item: EventStaff) => void }) {
  const columns: DataTableColumn<EventStaff>[] = [
    { key: "name", header: "Nombre", className: "min-w-[140px]", cell: (item) => <span className="font-semibold">{item.user?.full_name || item.user_id}</span> },
    { key: "email", header: "Email", className: "min-w-[245px]", cell: (item) => item.user?.email || "-" },
    { key: "role", header: "Rol global", cell: (item) => item.user?.role ? <RoleBadge role={item.user.role} /> : "-" },
    { key: "event_role", header: "Rol evento", cell: (item) => <StaffRoleBadge role={item.role_in_event} /> },
    { key: "context", header: "Contexto", className: "min-w-[180px]", cell: (item) => <span className="inline-block max-w-[180px] whitespace-normal rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold">{item.session_name || "General del evento"}</span> },
    { key: "start", header: "Inicio turno", cell: (item) => dateTime(item.shift_start) },
    { key: "end", header: "Fin turno", cell: (item) => dateTime(item.shift_end) },
    { key: "calendar_invitation", header: "Invitaciones", className: "min-w-[280px]", cell: invitationState }
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
