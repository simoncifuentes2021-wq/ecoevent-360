"use client";

import { Eye, Send, Trash2 } from "lucide-react";

import { ReportDownloadButton } from "@/components/reports/ReportDownloadButton";
import { ReportStatusBadge } from "@/components/reports/ReportStatusBadge";
import { Button } from "@/components/ui/button";
import { formatReportDate } from "@/lib/normalizers/reports";
import type { Report } from "@/types/report";

export function ReportCard({
  report,
  canDelete,
  canDeliver,
  onView,
  onDelete,
  onDeliver
}: {
  report: Report;
  canDelete?: boolean;
  canDeliver?: boolean;
  onView: (report: Report) => void;
  onDelete: (report: Report) => void;
  onDeliver: (report: Report) => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-bold text-slate-950">{report.title}</h3>
          <p className="text-sm text-slate-500">{formatReportDate(report.generated_at || report.created_at)}</p>
        </div>
        <ReportStatusBadge status={report.status} />
      </div>
      <p className="mt-3 line-clamp-2 text-sm text-slate-600">{report.summary || "Informe final preparado para entrega al cliente."}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        <Button onClick={() => onView(report)} size="sm" type="button" variant="secondary"><Eye className="h-4 w-4" />Ver</Button>
        <ReportDownloadButton report={report} />
        {canDeliver && report.status !== "DELIVERED" ? <Button onClick={() => onDeliver(report)} size="sm" type="button" variant="secondary"><Send className="h-4 w-4" />Entregar</Button> : null}
        {canDelete ? <Button onClick={() => onDelete(report)} size="sm" type="button" variant="secondary"><Trash2 className="h-4 w-4" />Anular</Button> : null}
      </div>
    </div>
  );
}
