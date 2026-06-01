"use client";

import { ExternalLink } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { ReportDownloadButton } from "@/components/reports/ReportDownloadButton";
import { ReportStatusBadge } from "@/components/reports/ReportStatusBadge";
import { Button } from "@/components/ui/button";
import { formatReportDate } from "@/lib/normalizers/reports";
import type { Report } from "@/types/report";

export function ReportDetailDrawer({ report, onClose }: { report: Report | null; onClose: () => void }) {
  if (!report) return null;
  const sections = Array.isArray(report.sections) ? report.sections : [];
  return (
    <ModalShell title={report.title} description="Detalle del informe generado para el evento." onClose={onClose}>
      <div className="space-y-4 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <ReportStatusBadge status={report.status} />
          <span className="text-slate-500">Generado: {formatReportDate(report.generated_at || report.created_at)}</span>
        </div>
        <p className="text-slate-600">{report.summary || "Reporte final con datos operativos, ambientales y de experiencia."}</p>
        <div className="grid gap-2 rounded-xl bg-slate-50 p-3">
          <span>Generado por: {report.generator?.full_name || report.generated_by || "Sistema"}</span>
          <span>Entregado: {formatReportDate(report.delivered_at)}</span>
          <span>Evento: {report.event?.name || report.event_id}</span>
          <span>Cliente: {report.event?.client?.business_name || "No informado"}</span>
        </div>
        {sections.length ? (
          <div>
            <h3 className="mb-2 font-semibold">Secciones incluidas</h3>
            <div className="flex flex-wrap gap-2">
              {sections.map((section, index) => <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700" key={index}>{typeof section === "string" ? section : section.label || section.key}</span>)}
            </div>
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <ReportDownloadButton report={report} />
          {report.pdf_url || report.file_url ? <Button onClick={() => window.open(report.pdf_url || report.file_url || "", "_blank")} type="button" variant="secondary"><ExternalLink className="h-4 w-4" />Abrir PDF</Button> : null}
        </div>
      </div>
    </ModalShell>
  );
}
