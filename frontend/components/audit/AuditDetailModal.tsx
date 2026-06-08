"use client";

import { X } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { AuditModuleBadge, AuditStatusBadge } from "@/components/audit/AuditBadges";
import { buildAuditDescription, formatAuditAction } from "@/lib/audit/formatAuditLog";
import type { AuditLog } from "@/types/auditLog";

function JsonBlock({ title, value }: { title: string; value?: Record<string, unknown> | null }) {
  return (
    <div>
      <h4 className="text-sm font-semibold">{title}</h4>
      <pre className="mt-2 max-h-56 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-50">
        {JSON.stringify(value || {}, null, 2)}
      </pre>
    </div>
  );
}

export function AuditDetailModal({ log, onClose }: { log: AuditLog | null; onClose: () => void }) {
  if (!log) return null;

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4">
      <div className="max-h-[92vh] w-full max-w-4xl overflow-hidden rounded-xl bg-white shadow-xl">
        <div className="flex items-start justify-between border-b p-5">
          <div>
            <p className="text-sm font-semibold uppercase text-primary">Detalle de auditoria</p>
            <h3 className="mt-1 text-2xl font-bold">{formatAuditAction(log.action)}</h3>
            <p className="mt-1 text-sm text-muted-foreground">{buildAuditDescription(log)}</p>
          </div>
          <Button variant="ghost" onClick={onClose} type="button">
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="max-h-[calc(92vh-96px)] space-y-5 overflow-y-auto p-5">
          <div className="grid gap-3 md:grid-cols-3">
            <Info label="Usuario" value={log.user_name || "Sistema"} />
            <Info label="Email" value={log.user_email || "-"} />
            <Info label="Rol" value={log.user_role || "-"} />
            <Info label="Fecha" value={new Date(log.created_at).toLocaleString("es-CL")} />
            <Info label="Modulo" value={<AuditModuleBadge module={log.module} />} />
            <Info label="Estado" value={<AuditStatusBadge status={log.status} />} />
            <Info label="Evento" value={log.event_name || "-"} />
            <Info label="Cliente" value={log.client_name || "-"} />
            <Info label="Zona" value={log.zone_name || "-"} />
            <Info label="Tarea" value={log.task_title || "-"} />
            <Info label="Incidencia" value={log.incident_title || "-"} />
            <Info label="Entidad" value={`${log.entity_type || "-"} ${log.entity_id || ""}`} />
            <Info label="IP" value={log.ip_address || "-"} />
            <Info label="Metodo" value={log.request_method || "-"} />
            <Info label="Ruta" value={log.request_path || "-"} />
            <Info label="Descripcion" value={log.description || buildAuditDescription(log)} />
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <JsonBlock title="Datos anteriores" value={log.old_data} />
            <JsonBlock title="Datos nuevos" value={log.new_data} />
            <JsonBlock title="Metadata" value={log.metadata} />
          </div>

          {log.user_agent ? (
            <div className="rounded-lg border bg-slate-50 p-3 text-xs text-muted-foreground">
              <span className="font-semibold text-foreground">User agent: </span>
              {log.user_agent}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="rounded-lg border bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <div className="mt-1 break-words text-sm font-medium">{value}</div>
    </div>
  );
}
