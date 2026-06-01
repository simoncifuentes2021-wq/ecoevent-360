"use client";

import { CheckCircle, Eye, Pencil, ShieldCheck } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { IncidentStatusBadge } from "@/components/incidents/IncidentStatusBadge";
import { IncidentTypeBadge } from "@/components/incidents/IncidentTypeBadge";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { Button } from "@/components/ui/button";
import type { Incident } from "@/types/incident";

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "-";
}

export function IncidentTable({
  incidents,
  loading,
  error,
  canEdit,
  canResolve,
  canClose,
  onView,
  onEdit,
  onResolve,
  onCloseIncident
}: {
  incidents: Incident[];
  loading?: boolean;
  error?: string | null;
  canEdit: boolean;
  canResolve: boolean;
  canClose: boolean;
  onView: (incident: Incident) => void;
  onEdit: (incident: Incident) => void;
  onResolve: (incident: Incident) => void;
  onCloseIncident: (incident: Incident) => void;
}) {
  const columns: DataTableColumn<Incident>[] = [
    { key: "title", header: "Incidencia", cell: (item) => <span className="font-semibold">{item.title}</span> },
    { key: "type", header: "Tipo", cell: (item) => <IncidentTypeBadge type={item.incident_type || item.type} /> },
    { key: "zone", header: "Zona", cell: (item) => item.zone?.name || "-" },
    { key: "priority", header: "Prioridad", cell: (item) => <PriorityBadge priority={item.priority} /> },
    { key: "status", header: "Estado", cell: (item) => <IncidentStatusBadge status={item.status} /> },
    { key: "reported", header: "Reportado por", cell: (item) => item.reporter?.full_name || item.reported_by || "-" },
    { key: "assigned", header: "Responsable", cell: (item) => item.assignee?.full_name || item.assigned_to || "-" },
    { key: "created", header: "Creada", cell: (item) => date(item.created_at) }
  ];

  return (
    <DataTable
      actions={(item) => (
        <div className="flex justify-end gap-2">
          <Button size="sm" variant="secondary" onClick={() => onView(item)}><Eye className="h-4 w-4" /></Button>
          {canEdit ? <Button size="sm" variant="secondary" onClick={() => onEdit(item)}><Pencil className="h-4 w-4" /></Button> : null}
          {canResolve && item.status !== "RESOLVED" && item.status !== "CLOSED" ? <Button size="sm" variant="ghost" onClick={() => onResolve(item)}><CheckCircle className="h-4 w-4" /></Button> : null}
          {canClose && item.status === "RESOLVED" ? <Button size="sm" variant="ghost" onClick={() => onCloseIncident(item)}><ShieldCheck className="h-4 w-4" /></Button> : null}
        </div>
      )}
      columns={columns}
      data={incidents}
      emptyDescription="Registra incidencias para resolver problemas reales del evento."
      emptyTitle="Sin incidencias"
      error={error}
      getRowKey={(item) => item.id}
      loading={loading}
    />
  );
}
