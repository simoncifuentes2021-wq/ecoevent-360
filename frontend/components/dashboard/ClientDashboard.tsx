import { BriefcaseBusiness, Cloud, FileText, Recycle } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import type { ClientDashboard as ClientDashboardType } from "@/types/dashboard";

export function ClientDashboard({ dashboard }: { dashboard: ClientDashboardType }) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      <KpiCard description="Eventos historicos" icon={BriefcaseBusiness} title="Mis eventos" value={dashboard.total_events} />
      <KpiCard description="En planificacion o ejecucion" icon={BriefcaseBusiness} title="Activos" tone="lime" value={dashboard.active_events} />
      <KpiCard description="Disponibles" icon={FileText} title="Reportes" value={dashboard.reports_available} />
      <KpiCard description={`${dashboard.total_carbon_tco2e.toFixed(2)} tCO2e`} icon={Cloud} title="Huella" tone="blue" value={`${dashboard.total_waste_kg.toFixed(0)} kg residuos`} />
      <KpiCard description="Gestion ambiental" icon={Recycle} title="Residuos" value={`${dashboard.total_waste_kg.toFixed(1)} kg`} />
    </div>
  );
}
