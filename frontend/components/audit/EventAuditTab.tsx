"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Eye, RefreshCcw, ShieldCheck } from "lucide-react";

import { AuditDetailModal } from "@/components/audit/AuditDetailModal";
import { AuditModuleBadge, AuditStatusBadge } from "@/components/audit/AuditBadges";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { FilterSelect } from "@/components/common/FilterSelect";
import { LoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { buildAuditDescription } from "@/lib/audit/formatAuditLog";
import { getEventAuditLogs } from "@/lib/api/auditLogs";
import type { AuditLog } from "@/types/auditLog";

const limit = 20;

export function EventAuditTab({ eventId }: { eventId: string }) {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const [module, setModule] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getEventAuditLogs(eventId, {
        module: module || undefined,
        status: status || undefined,
        page,
        limit
      });
      setItems(response.items);
      setTotal(response.total);
      setPages(response.pages);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la auditoria del evento.");
    } finally {
      setLoading(false);
    }
  }, [eventId, module, page, status]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo(() => `${total} movimientos registrados para este evento`, [total]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col justify-between gap-3 md:flex-row md:items-end">
        <div>
          <h2 className="text-2xl font-bold">Auditoria del evento</h2>
          <p className="text-muted-foreground">{summary}</p>
        </div>
        <Button variant="secondary" onClick={() => void load()} type="button">
          <RefreshCcw className="h-4 w-4" />
          Actualizar
        </Button>
      </div>

      <div className="grid gap-3 rounded-lg border bg-card p-4 md:grid-cols-2">
        <FilterSelect
          label="Modulo"
          value={module}
          onChange={(value) => {
            setModule(value);
            setPage(1);
          }}
          options={auditModuleOptions}
        />
        <FilterSelect
          label="Estado"
          value={status}
          onChange={(value) => {
            setStatus(value);
            setPage(1);
          }}
          options={auditStatusOptions}
        />
      </div>

      {loading ? <LoadingState label="Cargando trazabilidad..." /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && items.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-6 w-6" />}
          title="Sin auditoria para este evento"
          description="Cuando se creen tareas, incidencias, evidencias o registros ambientales, apareceran aqui."
        />
      ) : null}

      {!loading && !error && items.length > 0 ? (
        <div className="space-y-3">
          {items.map((log) => (
            <Card key={log.id}>
              <CardContent className="flex flex-col gap-3 p-4 md:flex-row md:items-center md:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <AuditModuleBadge module={log.module} />
                    <AuditStatusBadge status={log.status} />
                    <span className="text-xs text-muted-foreground">{new Date(log.created_at).toLocaleString("es-CL")}</span>
                  </div>
                  <p className="mt-2 font-semibold">{buildAuditDescription(log)}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {log.user_name || "Sistema"} - {log.zone_name || "Sin zona"} - {log.task_title || log.incident_title || log.entity_type || "Entidad"}
                  </p>
                </div>
                <Button variant="secondary" onClick={() => setSelected(log)} type="button">
                  <Eye className="h-4 w-4" />
                  Ver detalle
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : null}

      {pages > 1 ? (
        <div className="flex items-center justify-end gap-2">
          <Button disabled={page <= 1} variant="secondary" onClick={() => setPage(page - 1)} type="button">
            Anterior
          </Button>
          <span className="text-sm text-muted-foreground">Pagina {page} de {pages}</span>
          <Button disabled={page >= pages} variant="secondary" onClick={() => setPage(page + 1)} type="button">
            Siguiente
          </Button>
        </div>
      ) : null}

      <AuditDetailModal log={selected} onClose={() => setSelected(null)} />
    </div>
  );
}

const auditModuleOptions = [
  { label: "Todos", value: "" },
  { label: "Auth", value: "auth" },
  { label: "Usuarios", value: "users" },
  { label: "Clientes", value: "clients" },
  { label: "Eventos", value: "events" },
  { label: "Servicios", value: "services" },
  { label: "Zonas", value: "zones" },
  { label: "Personal", value: "staff" },
  { label: "Tareas", value: "tasks" },
  { label: "Incidencias", value: "incidents" },
  { label: "Evidencias", value: "evidences" },
  { label: "Residuos", value: "waste" },
  { label: "Huella", value: "carbon" },
  { label: "Consumos", value: "operations" },
  { label: "Reportes", value: "reports" }
];

const auditStatusOptions = [
  { label: "Todos", value: "" },
  { label: "Exitoso", value: "SUCCESS" },
  { label: "Fallido", value: "FAILED" },
  { label: "Denegado", value: "DENIED" },
  { label: "Info", value: "INFO" }
];
