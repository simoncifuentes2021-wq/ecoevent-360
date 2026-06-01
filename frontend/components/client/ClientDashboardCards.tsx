import { BarChart3, CalendarDays, Cloud, FileText, Recycle, Star } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import { formatClientMetric, formatClientPercentage } from "@/lib/normalizers/clientDashboard";
import type { ClientDashboard } from "@/types/clientDashboard";

export function ClientDashboardCards({ dashboard }: { dashboard: ClientDashboard }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
      <KpiCard description="En planificacion o ejecucion" icon={CalendarDays} title="Eventos activos" value={dashboard.active_events} />
      <KpiCard description="Total historico" icon={BarChart3} title="Eventos" tone="lime" value={dashboard.total_events} />
      <KpiCard description="Disponibles" icon={FileText} title="Reportes" tone="blue" value={dashboard.reports_available} />
      <KpiCard description={`${formatClientPercentage(dashboard.recovery_rate)} recuperacion`} icon={Recycle} title="Residuos kg" value={formatClientMetric(dashboard.total_waste_kg)} />
      <KpiCard description="Huella acumulada" icon={Cloud} title="tCO2e" tone="slate" value={formatClientMetric(dashboard.total_carbon_tco2e)} />
      <KpiCard description="Promedio encuestas" icon={Star} title="Satisfaccion" tone="lime" value={dashboard.average_satisfaction ? dashboard.average_satisfaction.toFixed(1) : "0.0"} />
    </div>
  );
}
