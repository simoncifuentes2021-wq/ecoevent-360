import { BarChart3, CalendarDays, Cloud, FileText, Recycle, Star } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import { formatClientMetric, formatClientPercentage } from "@/lib/normalizers/clientDashboard";
import type { ClientDashboard } from "@/types/clientDashboard";

export function ClientDashboardCards({ dashboard }: { dashboard: ClientDashboard }) {
  const cards = [
    dashboard.active_events > 0 ? <KpiCard description="En planificacion o ejecucion" icon={CalendarDays} title="Eventos activos" value={dashboard.active_events} /> : null,
    dashboard.total_events > 0 ? <KpiCard description="Total historico" icon={BarChart3} title="Eventos" tone="lime" value={dashboard.total_events} /> : null,
    dashboard.reports_available > 0 ? <KpiCard description="Disponibles" icon={FileText} title="Reportes" tone="blue" value={dashboard.reports_available} /> : null,
    dashboard.total_waste_kg > 0 ? <KpiCard description={`${formatClientPercentage(dashboard.recovery_rate)} recuperacion`} icon={Recycle} title="Residuos kg" value={formatClientMetric(dashboard.total_waste_kg)} /> : null,
    dashboard.total_carbon_tco2e > 0 ? <KpiCard description="Huella acumulada" icon={Cloud} title="tCO2e" tone="slate" value={formatClientMetric(dashboard.total_carbon_tco2e)} /> : null,
    dashboard.average_satisfaction > 0 ? <KpiCard description="Promedio de experiencia" icon={Star} title="Satisfaccion" tone="lime" value={dashboard.average_satisfaction.toFixed(1)} /> : null
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card, index) => card ? <div key={index}>{card}</div> : null)}
    </div>
  );
}
