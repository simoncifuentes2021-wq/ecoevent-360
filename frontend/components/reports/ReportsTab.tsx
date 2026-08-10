"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/common/ErrorState";
import { GenerateReportButton } from "@/components/reports/GenerateReportButton";
import { ReportDraftDialog } from "@/components/reports/ReportDraftDialog";
import { MarkReportDeliveredDialog } from "@/components/reports/MarkReportDeliveredDialog";
import { ReportDeleteDialog } from "@/components/reports/ReportDeleteDialog";
import { ReportDetailDrawer } from "@/components/reports/ReportDetailDrawer";
import { ReportEmptyState } from "@/components/reports/ReportEmptyState";
import { ReportList } from "@/components/reports/ReportList";
import { ReportPreviewPanel } from "@/components/reports/ReportPreviewPanel";
import { createReportDraft, deleteReport, getEventReports, markReportDelivered } from "@/lib/api/reports";
import { normalizeGenerateReportResponse, normalizeReport } from "@/lib/normalizers/reports";
import { canDeleteReports, canGenerateReports, canMarkReportDelivered, canViewReportPreview } from "@/lib/permissions";
import type { UserRole } from "@/types/roles";
import type { Report, ReportScope } from "@/types/report";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export function ReportsTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const router = useRouter();
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generateOpen, setGenerateOpen] = useState(false);
  const [detail, setDetail] = useState<Report | null>(null);
  const [deleting, setDeleting] = useState<Report | null>(null);
  const [delivering, setDelivering] = useState<Report | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getEventReports(eventId);
      setReports(data.items.map(normalizeReport));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los reportes.");
      setReports([]);
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  async function generate(scope: ReportScope, sessionId?: string) {
    setSaving(true);
    try {
      const response = await createReportDraft(eventId, scope, sessionId);
      setGenerateOpen(false);
      router.push(`/reports/${response.id}/edit`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "El generador de reportes aun no esta disponible en el backend.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    setSaving(true);
    try {
      await deleteReport(deleting.id);
      setDeleting(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo anular el reporte.");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelivered() {
    if (!delivering) return;
    setSaving(true);
    try {
      await markReportDelivered(delivering.id);
      setDelivering(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Accion no disponible en backend.");
    } finally {
      setSaving(false);
    }
  }

  const canGenerate = canGenerateReports(role);
  const canDelete = canDeleteReports(role);
  const canDeliver = canMarkReportDelivered(role);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Reportes profesionales</h2>
          <p className="text-sm text-slate-600">Genera, descarga y gestiona informes finales listos para entregar al cliente.</p>
        </div>
        {canGenerate ? <GenerateReportButton onClick={() => setGenerateOpen(true)} /> : null}
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {canViewReportPreview(role) ? <ReportPreviewPanel eventId={eventId} /> : null}
      {reports.length || loading || error ? (
        <ReportList
          canDelete={canDelete}
          canDeliver={canDeliver}
          error={null}
          loading={loading}
          reports={reports}
          onDelete={setDeleting}
          onDeliver={setDelivering}
          onView={(report) => report.status === "DRAFT" ? router.push(`/reports/${report.id}/edit`) : setDetail(report)}
        />
      ) : <ReportEmptyState />}
      <ReportDraftDialog eventId={eventId} loading={saving} open={generateOpen} onClose={() => setGenerateOpen(false)} onCreate={generate} />
      <ReportDeleteDialog loading={saving} report={deleting} onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
      <MarkReportDeliveredDialog loading={saving} report={delivering} onClose={() => setDelivering(null)} onConfirm={confirmDelivered} />
      <ReportDetailDrawer report={detail} onClose={() => setDetail(null)} />
    </div>
  );
}
