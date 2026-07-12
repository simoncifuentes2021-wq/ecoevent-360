"use client";

import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, Cloud, FileText, Recycle, ShieldAlert } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { ReportSectionChecklist } from "@/components/reports/ReportSectionChecklist";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { getCarbonSummary } from "@/lib/api/carbon";
import { getEventDashboard } from "@/lib/api/dashboards";
import { getEvent } from "@/lib/api/events";
import { getEventServices } from "@/lib/api/eventServices";
import { getEventEvidences } from "@/lib/api/evidences";
import { getEventIncidents } from "@/lib/api/incidents";
import { getEventTasks } from "@/lib/api/tasks";
import { getWasteSummary } from "@/lib/api/waste";
import { buildEventDashboardFromFallbackData, normalizeEventDashboard } from "@/lib/normalizers/dashboard";
import { buildReportSectionChecklist, previewFromDashboard } from "@/lib/normalizers/reports";
import type { ReportPreview } from "@/types/report";

export function ReportPreviewPanel({ eventId }: { eventId: string }) {
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const dashboard = normalizeEventDashboard(await getEventDashboard(eventId));
      setPreview(previewFromDashboard(dashboard));
    } catch {
      const [eventData, services, tasks, incidents, evidences, wasteSummary, carbonSummary] = await Promise.allSettled([
        getEvent(eventId),
        getEventServices(eventId),
        getEventTasks(eventId),
        getEventIncidents(eventId),
        getEventEvidences(eventId),
        getWasteSummary(eventId),
        getCarbonSummary(eventId)
      ]);
      const dashboard = buildEventDashboardFromFallbackData({
        event: eventData.status === "fulfilled" ? eventData.value : undefined,
        tasks: tasks.status === "fulfilled" ? tasks.value.items : [],
        incidents: incidents.status === "fulfilled" ? incidents.value.items : [],
        wasteSummary: wasteSummary.status === "fulfilled" ? wasteSummary.value : null,
        carbonSummary: carbonSummary.status === "fulfilled" ? carbonSummary.value : null,
        surveys: []
      });
      const next = previewFromDashboard(dashboard);
      next.services_count = services.status === "fulfilled" ? services.value.length : 0;
      next.evidences_count = evidences.status === "fulfilled" ? evidences.value.items.length : 0;
      setPreview(next);
      if (![eventData, services, tasks, incidents, evidences, wasteSummary, carbonSummary].some((item) => item.status === "fulfilled")) {
        setError("No se pudo construir la vista previa del reporte.");
      }
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <LoadingState label="Preparando vista previa..." />;
  if (!preview) return <ErrorState message={error || "No se pudo cargar la vista previa."} onRetry={load} />;

  return (
    <Card>
      <CardHeader>
        <h3 className="font-bold text-slate-950">Vista previa ejecutiva</h3>
        <p className="text-sm text-slate-600">Datos que probablemente entraran al reporte final. No bloquea la generacion.</p>
      </CardHeader>
      <CardContent className="space-y-4">
        {error ? <ErrorState message={error} title="Datos parciales" onRetry={load} /> : null}
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <KpiCard description={`${preview.tasks_completed}/${preview.tasks_total} completadas`} icon={ClipboardCheck} title="Tareas" value={preview.tasks_total} />
          <KpiCard description={`${preview.incidents_resolved} resueltas`} icon={ShieldAlert} title="Incidencias" tone="slate" value={preview.incidents_total} />
          <KpiCard description={`${preview.waste_recovery_rate.toFixed(0)}% recuperacion`} icon={Recycle} title="Residuos kg" value={preview.waste_total_kg.toFixed(1)} />
          <KpiCard description={`${preview.carbon_kgco2e_per_attendee.toFixed(1)} kg/asistente`} icon={Cloud} title="Huella tCO2e" tone="blue" value={preview.carbon_total_tco2e.toFixed(2)} />
          <KpiCard description={`Nota ${preview.survey_average_rating.toFixed(1)}`} icon={FileText} title="Formularios" tone="lime" value={preview.survey_total_responses} />
        </div>
        <ReportSectionChecklist sections={buildReportSectionChecklist(preview)} />
      </CardContent>
    </Card>
  );
}
