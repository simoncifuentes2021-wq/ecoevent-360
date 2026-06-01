"use client";

import { CalendarClock, MapPin, User } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { IncidentStatusBadge } from "@/components/incidents/IncidentStatusBadge";
import { IncidentTypeBadge } from "@/components/incidents/IncidentTypeBadge";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { Button } from "@/components/ui/button";
import type { Incident } from "@/types/incident";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function IncidentDetailDrawer({ incident, canResolve, canClose, onClose, onResolve, onCloseIncident }: { incident: Incident; canResolve: boolean; canClose: boolean; onClose: () => void; onResolve: () => void; onCloseIncident: () => void }) {
  return (
    <ModalShell title={incident.title} description={incident.description} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2"><IncidentStatusBadge status={incident.status} /><IncidentTypeBadge type={incident.incident_type || incident.type} /><PriorityBadge priority={incident.priority} /></div>
        <Info icon={<MapPin className="h-4 w-4" />} label="Zona" value={incident.zone?.name || "Sin zona"} />
        <Info icon={<User className="h-4 w-4" />} label="Reportado por" value={incident.reporter?.full_name || incident.reported_by || "-"} />
        <Info icon={<User className="h-4 w-4" />} label="Responsable" value={incident.assignee?.full_name || incident.assigned_to || "Sin asignar"} />
        <Info icon={<CalendarClock className="h-4 w-4" />} label="Creada" value={date(incident.created_at)} />
        <Info icon={<CalendarClock className="h-4 w-4" />} label="Resuelta" value={date(incident.resolved_at)} />
        {incident.solution ? <div className="rounded-2xl bg-emerald-50 p-4 text-sm text-emerald-900"><p className="font-semibold">Solucion</p><p className="mt-1">{incident.solution}</p></div> : null}
        <div className="grid gap-2 md:grid-cols-2">
          {canResolve && incident.status !== "RESOLVED" && incident.status !== "CLOSED" ? <Button onClick={onResolve}>Resolver</Button> : null}
          {canClose && incident.status === "RESOLVED" ? <Button variant="secondary" onClick={onCloseIncident}>Cerrar</Button> : null}
        </div>
      </div>
    </ModalShell>
  );
}

function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border p-3 text-sm"><span className="text-emerald-700">{icon}</span><span className="font-semibold">{label}:</span><span className="text-slate-600">{value}</span></div>;
}
