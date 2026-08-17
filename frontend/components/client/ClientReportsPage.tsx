"use client";

import { useEffect, useState } from "react";
import { Download, Eye } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ReportStatusBadge } from "@/components/reports/ReportStatusBadge";
import { Button } from "@/components/ui/button";
import { getEvents } from "@/lib/api/events";
import { downloadReportPublication, getEventReports, getReportPublications } from "@/lib/api/reports";
import type { Report, ReportPublication } from "@/types/report";

type DeliveredReportRow = {
  id: string;
  title: string;
  event_name: string;
  scope: string;
  status: string;
  delivered_at: string | null;
  report: Report;
  publication: ReportPublication;
};

export function ClientReportsPage() {
  const [items, setItems] = useState<DeliveredReportRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opening, setOpening] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const events = await getEvents({ page: 1, limit: 100 });
        const settled = await Promise.allSettled(events.items.map(async event => {
          const reports = await getEventReports(event.id);
          const versions = await Promise.all(reports.items.map(async report => ({
            report,
            publications: await getReportPublications(report.id),
          })));
          return versions.flatMap(({ report, publications }) => publications
            .filter(publication => publication.status === "DELIVERED")
            .map(publication => ({
              id: publication.id,
              title: report.title,
              event_name: event.name,
              scope: report.scope === "SHOW" ? "Show" : "Evento",
              status: publication.status,
              delivered_at: publication.delivered_at || null,
              report,
              publication,
            })));
        }));
        setItems(settled.flatMap(result => result.status === "fulfilled" ? result.value : []));
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : "No se pudieron cargar tus reportes.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  async function openPublication(item: DeliveredReportRow, inline: boolean) {
    setOpening(item.id);
    setError(null);
    try {
      const blob = await downloadReportPublication(item.publication.id, inline);
      const url = URL.createObjectURL(blob);
      if (inline) {
        const popup = window.open(url, "_blank", "noopener,noreferrer");
        if (!popup) throw new Error("El navegador bloqueó la nueva pestaña. Habilita las ventanas emergentes.");
      } else {
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = `${item.title.replace(/[^a-z0-9áéíóúñ_-]+/gi, "-")}-v${item.publication.publication_number}.pdf`;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo obtener el PDF entregado.");
    } finally {
      setOpening(null);
    }
  }

  const columns: DataTableColumn<DeliveredReportRow>[] = [
    { key: "title", header: "Reporte", cell: item => <div><span className="font-semibold">{item.title}</span><span className="mt-1 block text-xs text-slate-500">Versión {item.publication.publication_number} · {item.publication.page_count} páginas</span></div> },
    { key: "event", header: "Evento", cell: item => item.event_name },
    { key: "scope", header: "Alcance", cell: item => item.scope },
    { key: "status", header: "Estado", cell: item => <ReportStatusBadge status={item.status} /> },
    { key: "date", header: "Entregado", cell: item => item.delivered_at ? new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", dateStyle: "medium" }).format(new Date(item.delivered_at)) : "-" },
  ];

  return <DataTable
    actions={item => <div className="flex justify-end gap-2"><Button disabled={opening === item.id} onClick={() => void openPublication(item, true)} size="sm" type="button" variant="secondary"><Eye className="h-4 w-4"/>Ver PDF</Button><Button disabled={opening === item.id} onClick={() => void openPublication(item, false)} size="sm" type="button"><Download className="h-4 w-4"/>{opening === item.id ? "Preparando…" : "Descargar"}</Button></div>}
    columns={columns}
    data={items}
    emptyDescription="El administrador todavía no ha entregado una versión PDF premium."
    emptyTitle="Sin reportes entregados"
    error={error}
    getRowKey={item => item.id}
    loading={loading}
  />;
}
