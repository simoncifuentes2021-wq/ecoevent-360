"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Eye } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ReportDetailDrawer } from "@/components/reports/ReportDetailDrawer";
import { ReportDownloadButton } from "@/components/reports/ReportDownloadButton";
import { ReportStatusBadge } from "@/components/reports/ReportStatusBadge";
import { Button } from "@/components/ui/button";
import { getEvents } from "@/lib/api/events";
import { getEventReports } from "@/lib/api/reports";
import { formatReportDate, normalizeReport } from "@/lib/normalizers/reports";
import type { Report } from "@/types/report";

type ReportRow = Report & { event_name?: string };

export function ClientReportsPage() {
  const [reports, setReports] = useState<ReportRow[]>([]);
  const [detail, setDetail] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const events = await getEvents({ page: 1, limit: 100 });
        const settled = await Promise.allSettled(events.items.map(async (event) => {
          const data = await getEventReports(event.id);
          return data.items.map((report) => ({ ...normalizeReport(report), event_name: event.name }));
        }));
        setReports(settled.flatMap((item) => item.status === "fulfilled" ? item.value : []));
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar tus reportes.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  const columns: DataTableColumn<ReportRow>[] = [
    { key: "title", header: "Reporte", cell: (report) => <span className="font-semibold">{report.title}</span> },
    { key: "event", header: "Evento", cell: (report) => report.event_name || report.event?.name || "-" },
    { key: "status", header: "Estado", cell: (report) => <ReportStatusBadge status={report.status} /> },
    { key: "date", header: "Fecha", cell: (report) => formatReportDate(report.generated_at || report.created_at) }
  ];

  return (
    <>
      <DataTable
        actions={(report) => <div className="flex justify-end gap-2"><Button onClick={() => setDetail(report)} size="sm" type="button" variant="secondary"><Eye className="h-4 w-4" /></Button><ReportDownloadButton report={report} />{report.event_id ? <Link href={`/client/eventos/${report.event_id}`}><Button size="sm" type="button" variant="secondary">Evento</Button></Link> : null}</div>}
        columns={columns}
        data={reports}
        emptyDescription="Aun no hay reportes disponibles para tus eventos."
        emptyTitle="Sin reportes"
        error={error}
        getRowKey={(report) => report.id}
        loading={loading}
      />
      <ReportDetailDrawer report={detail} onClose={() => setDetail(null)} />
    </>
  );
}
