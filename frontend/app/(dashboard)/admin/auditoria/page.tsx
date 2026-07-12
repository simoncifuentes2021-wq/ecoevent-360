"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, Eye, RefreshCcw, ShieldCheck } from "lucide-react";

import { AuditDetailModal } from "@/components/audit/AuditDetailModal";
import { AuditModuleBadge, AuditStatusBadge } from "@/components/audit/AuditBadges";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { FilterSelect } from "@/components/common/FilterSelect";
import { PageHeader } from "@/components/common/PageHeader";
import { SearchInput } from "@/components/common/SearchInput";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { buildAuditDescription, formatAuditAction } from "@/lib/audit/formatAuditLog";
import { exportAuditLogs, getAuditLogs } from "@/lib/api/auditLogs";
import type { AuditLog, AuditLogFilters, AuditLogSummary } from "@/types/auditLog";

const limit = 20;

export default function AdminAuditPage() {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [selected, setSelected] = useState<AuditLog | null>(null);
  const [filters, setFilters] = useState<AuditLogFilters>({ page: 1, limit });
  const [draft, setDraft] = useState<AuditLogFilters>({ page: 1, limit });
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const page = filters.page || 1;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getAuditLogs({ ...filters, page, limit });
      setItems(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los registros de auditoria.");
    } finally {
      setLoading(false);
    }
  }, [filters, page]);

  useEffect(() => {
    void load();
  }, [load]);

  const summary = useMemo<AuditLogSummary>(() => {
    const today = new Date().toISOString().slice(0, 10);
    const moduleCounts = items.reduce<Record<string, number>>((acc, item) => {
      acc[item.module] = (acc[item.module] || 0) + 1;
      return acc;
    }, {});
    const topModule = Object.entries(moduleCounts).sort((a, b) => b[1] - a[1])[0]?.[0] || "-";
    return {
      total,
      today: items.filter((item) => item.created_at.startsWith(today)).length,
      failedOrDenied: items.filter((item) => ["FAILED", "DENIED"].includes(item.status)).length,
      topModule,
      lastMovement: items[0] ? new Date(items[0].created_at).toLocaleString("es-CL") : "-"
    };
  }, [items, total]);

  async function downloadCsv() {
    setExporting(true);
    try {
      const blob = await exportAuditLogs(filters);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "audit-logs.csv";
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  }

  function applyFilters() {
    setFilters({ ...draft, page: 1, limit });
  }

  function clearFilters() {
    const empty = { page: 1, limit };
    setDraft(empty);
    setFilters(empty);
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Control interno"
          title="Auditoria del sistema"
          description="Revisa los movimientos importantes realizados por usuarios dentro de EcoEvent 360."
          actions={
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => void load()} type="button">
                <RefreshCcw className="h-4 w-4" />
                Actualizar
              </Button>
              <Button disabled={exporting} onClick={() => void downloadCsv()} type="button">
                <Download className="h-4 w-4" />
                {exporting ? "Exportando..." : "Exportar CSV"}
              </Button>
            </div>
          }
        />

        <div className="grid gap-4 md:grid-cols-5">
          <AuditKpi label="Total movimientos" value={summary.total.toString()} />
          <AuditKpi label="Movimientos de hoy" value={summary.today.toString()} />
          <AuditKpi label="Fallidos o denegados" value={summary.failedOrDenied.toString()} />
          <AuditKpi label="Modulo mas activo" value={summary.topModule} />
          <AuditKpi label="Ultimo movimiento" value={summary.lastMovement} />
        </div>

        <Card>
          <CardContent className="space-y-4">
            <div className="grid gap-3 md:grid-cols-4">
              <SearchInput
                placeholder="Buscar usuario, evento, cliente o accion..."
                value={draft.q || ""}
                onChange={(value) => setDraft((current) => ({ ...current, q: value }))}
              />
              <FilterSelect label="Modulo" value={draft.module || ""} onChange={(value) => setDraft((current) => ({ ...current, module: value }))} options={auditModuleOptions} />
              <FilterSelect label="Accion" value={draft.action || ""} onChange={(value) => setDraft((current) => ({ ...current, action: value }))} options={auditActionOptions} />
              <FilterSelect label="Estado" value={draft.status || ""} onChange={(value) => setDraft((current) => ({ ...current, status: value }))} options={auditStatusOptions} />
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Usuario ID" value={draft.user_id || ""} onChange={(event) => setDraft((current) => ({ ...current, user_id: event.target.value }))} />
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Evento ID" value={draft.event_id || ""} onChange={(event) => setDraft((current) => ({ ...current, event_id: event.target.value }))} />
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Cliente ID" value={draft.client_id || ""} onChange={(event) => setDraft((current) => ({ ...current, client_id: event.target.value }))} />
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Zona ID" value={draft.zone_id || ""} onChange={(event) => setDraft((current) => ({ ...current, zone_id: event.target.value }))} />
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Tarea ID" value={draft.task_id || ""} onChange={(event) => setDraft((current) => ({ ...current, task_id: event.target.value }))} />
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Incidencia ID" value={draft.incident_id || ""} onChange={(event) => setDraft((current) => ({ ...current, incident_id: event.target.value }))} />
              <input className="h-10 rounded-md border px-3 text-sm" placeholder="Entidad ID" value={draft.entity_id || ""} onChange={(event) => setDraft((current) => ({ ...current, entity_id: event.target.value }))} />
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_1fr_auto_auto]">
              <input className="h-10 rounded-md border px-3 text-sm" type="datetime-local" value={draft.from_date || ""} onChange={(event) => setDraft((current) => ({ ...current, from_date: event.target.value }))} />
              <input className="h-10 rounded-md border px-3 text-sm" type="datetime-local" value={draft.to_date || ""} onChange={(event) => setDraft((current) => ({ ...current, to_date: event.target.value }))} />
              <Button onClick={applyFilters} type="button">Aplicar filtros</Button>
              <Button variant="secondary" onClick={clearFilters} type="button">Limpiar</Button>
            </div>
          </CardContent>
        </Card>

        <DataTable
          columns={columns}
          data={items}
          emptyDescription="Cuando se ejecuten acciones auditadas, apareceran aqui con fecha, usuario y contexto."
          emptyTitle="Aun no hay registros de auditoria"
          error={error}
          getRowKey={(row) => row.id}
          limit={limit}
          loading={loading}
          page={page}
          total={total}
          onPageChange={(nextPage) => setFilters((current) => ({ ...current, page: nextPage }))}
          actions={(row) => (
            <Button variant="secondary" size="sm" onClick={() => setSelected(row)} type="button">
              <Eye className="h-4 w-4" />
              Ver detalle
            </Button>
          )}
        />

        <AuditDetailModal log={selected} onClose={() => setSelected(null)} />
      </div>
    </RoleGuard>
  );
}

function AuditKpi({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-emerald-50 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
            <p className="truncate text-lg font-bold">{value}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

const columns: DataTableColumn<AuditLog>[] = [
  { key: "created_at", header: "Fecha/hora", cell: (row) => new Date(row.created_at).toLocaleString("es-CL") },
  {
    key: "user",
    header: "Usuario",
    cell: (row) => (
      <div>
        <p className="font-medium">{row.user_name || "Sistema"}</p>
        <p className="text-xs text-muted-foreground">{row.user_role || row.user_email || "-"}</p>
      </div>
    )
  },
  {
    key: "description",
    header: "Descripcion",
    cell: (row) => <p className="min-w-[260px] max-w-[420px] whitespace-normal font-medium">{buildAuditDescription(row)}</p>
  },
  {
    key: "event",
    header: "Evento",
    cell: (row) => (
      <div>
        <p className="max-w-[180px] truncate">{row.event_name || "Sin evento"}</p>
        <p className="max-w-[180px] truncate text-xs text-muted-foreground">{row.client_name || "Sin cliente"}</p>
      </div>
    )
  },
  { key: "zone", header: "Zona", cell: (row) => <span>{row.zone_name || "-"}</span> },
  {
    key: "entity",
    header: "Entidad",
    cell: (row) => (
      <div>
        <p>{row.task_title || row.incident_title || row.entity_type || "-"}</p>
        <p className="max-w-[160px] truncate text-xs text-muted-foreground">{row.entity_id || row.task_id || row.incident_id || "-"}</p>
      </div>
    )
  },
  { key: "module", header: "Modulo", cell: (row) => <AuditModuleBadge module={row.module} /> },
  { key: "action", header: "Accion", cell: (row) => <span className="font-semibold">{formatAuditAction(row.action)}</span> },
  { key: "status", header: "Estado", cell: (row) => <AuditStatusBadge status={row.status} /> },
  { key: "ip", header: "IP", cell: (row) => <span className="text-xs text-muted-foreground">{row.ip_address || "-"}</span> }
];

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

const auditActionOptions = [
  { label: "Todas", value: "" },
  { label: "Login exitoso", value: "LOGIN_SUCCESS" },
  { label: "Login fallido", value: "LOGIN_FAILED" },
  { label: "Evento creado", value: "EVENT_CREATED" },
  { label: "Cambio estado evento", value: "EVENT_STATUS_CHANGED" },
  { label: "Tarea completada", value: "COMPLETE" },
  { label: "Incidencia resuelta", value: "RESOLVE" },
  { label: "Residuo creado", value: "CREATE" },
  { label: "CSV importado", value: "SURVEY_CSV_IMPORTED" }
];

const auditStatusOptions = [
  { label: "Todos", value: "" },
  { label: "Exitoso", value: "SUCCESS" },
  { label: "Fallido", value: "FAILED" },
  { label: "Denegado", value: "DENIED" },
  { label: "Info", value: "INFO" }
];
