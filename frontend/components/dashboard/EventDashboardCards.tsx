import { AlertTriangle, CheckCircle, ClipboardList, Cloud, Recycle, Star } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import { formatDashboardPercentage } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";

export function EventDashboardCards({ dashboard }: { dashboard: EventDashboard }) {
  const cards = [];
  if (dashboard.tasks.total > 0) cards.push(<KpiCard key="tasks" description="Planificadas" icon={ClipboardList} title="Tareas" value={dashboard.tasks.total} />);
  if (dashboard.tasks.completed > 0) cards.push(<KpiCard key="completed" description={formatDashboardPercentage(dashboard.tasks.completion_rate)} icon={CheckCircle} title="Completadas" tone="lime" value={dashboard.tasks.completed} />);
  if (dashboard.incidents.open > 0) cards.push(<KpiCard key="incidents" description="Abiertas" icon={AlertTriangle} title="Incidencias" tone="slate" value={dashboard.incidents.open} />);
  if (dashboard.waste.total_kg > 0) cards.push(<KpiCard key="waste" description={`${formatDashboardPercentage(dashboard.waste.recovery_rate)} recuperación`} icon={Recycle} title="Residuos kg" value={dashboard.waste.total_kg.toFixed(1)} />);
  if (dashboard.carbon.total_kgco2e > 0) cards.push(<KpiCard key="carbon" description={`${dashboard.carbon.kgco2e_per_attendee.toFixed(1)} kg por asistente`} icon={Cloud} title="Huella tCO2e" tone="blue" value={dashboard.carbon.total_tco2e.toFixed(2)} />);
  if (dashboard.survey.total_responses > 0) cards.push(<KpiCard key="survey" description={`${formatDashboardPercentage(dashboard.survey.recommendation_rate)} recomienda`} icon={Star} title="Encuesta" tone="lime" value={dashboard.survey.average_rating ? dashboard.survey.average_rating.toFixed(1) : "0.0"} />);

  return cards.length ? <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{cards}</div> : null;
}
