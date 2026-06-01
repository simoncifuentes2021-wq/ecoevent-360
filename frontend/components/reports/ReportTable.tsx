"use client";

import { Eye, Send, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ReportDownloadButton } from "@/components/reports/ReportDownloadButton";
import { ReportStatusBadge } from "@/components/reports/ReportStatusBadge";
import { Button } from "@/components/ui/button";
import { formatReportDate } from "@/lib/normalizers/reports";
import type { Report } from "@/types/report";

export function ReportTable({
  reports,
  loading,
  error,
  canDelete,
  canDeliver,
  onView,
  onDelete,
  onDeliver
}: {
  reports: Report[];
  loading?: boolean;
  error?: string | null;
  canDelete?: boolean;
  canDeliver?: boolean;
  onView: (report: Report) => void;
  onDelete: (report: Report) => void;
  onDeliver: (report: Report) => void;
}) {
  const columns: DataTableColumn<Report>[] = [
    { key: "title", header: "Reporte", cell: (report) => <div><p className="font-semibold text-slate-950">{report.title}</p><p className="text-xs text-slate-500">{report.summary || "Reporte final del evento"}</p></div> },
    { key: "status", header: "Estado", cell: (report) => <ReportStatusBadge status={report.status} /> },
    { key: "generated", header: "Generado", cell: (report) => formatReportDate(report.generated_at || report.created_at) },
    { key: "delivered", header: "Entregado", cell: (report) => formatReportDate(report.delivered_at) },
    { key: "generator", header: "Generado por", cell: (report) => report.generator?.full_name || report.generated_by || "Sistema" }
  ];

  return (
    <DataTable
      actions={(report) => (
        <div className="flex justify-end gap-2">
          <Button onClick={() => onView(report)} size="sm" type="button" variant="secondary"><Eye className="h-4 w-4" /></Button>
          <ReportDownloadButton report={report} />
          {canDeliver && report.status !== "DELIVERED" ? <Button onClick={() => onDeliver(report)} size="sm" type="button" variant="secondary"><Send className="h-4 w-4" /></Button> : null}
          {canDelete ? <Button onClick={() => onDelete(report)} size="sm" type="button" variant="secondary"><Trash2 className="h-4 w-4" /></Button> : null}
        </div>
      )}
      columns={columns}
      data={reports}
      emptyDescription="Cuando generes el informe final, aparecera aqui para descargarlo o entregarlo al cliente."
      emptyTitle="Aun no hay reportes generados"
      error={error}
      getRowKey={(report) => report.id}
      loading={loading}
    />
  );
}
