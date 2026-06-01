import { AlertTriangle, CheckCircle, ClipboardList, Cloud, Recycle, Star } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import { formatDashboardPercentage } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";

export function EventDashboardCards({ dashboard }: { dashboard: EventDashboard }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
      <KpiCard description="Planificadas" icon={ClipboardList} title="Tareas" value={dashboard.tasks.total} />
      <KpiCard description={formatDashboardPercentage(dashboard.tasks.completion_rate)} icon={CheckCircle} title="Completadas" tone="lime" value={dashboard.tasks.completed} />
      <KpiCard description="Abiertas" icon={AlertTriangle} title="Incidencias" tone="slate" value={dashboard.incidents.open} />
      <KpiCard description={`${formatDashboardPercentage(dashboard.waste.recovery_rate)} recuperacion`} icon={Recycle} title="Residuos kg" value={dashboard.waste.total_kg.toFixed(1)} />
      <KpiCard description={`${dashboard.carbon.kgco2e_per_attendee.toFixed(1)} kg por asistente`} icon={Cloud} title="Huella tCO2e" tone="blue" value={dashboard.carbon.total_tco2e.toFixed(2)} />
      <KpiCard description={`${formatDashboardPercentage(dashboard.survey.recommendation_rate)} recomienda`} icon={Star} title="Encuesta" tone="lime" value={dashboard.survey.average_rating ? dashboard.survey.average_rating.toFixed(1) : "0.0"} />
    </div>
  );
}
