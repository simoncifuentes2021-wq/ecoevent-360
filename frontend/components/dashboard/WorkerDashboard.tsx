import { CheckCircle, ClipboardList, ShieldAlert } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import type { WorkerDashboard as WorkerDashboardType } from "@/types/dashboard";

export function WorkerDashboard({ dashboard }: { dashboard: WorkerDashboardType }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <KpiCard description="Para hoy o proximas" icon={ClipboardList} title="Pendientes" value={dashboard.pending_tasks} />
      <KpiCard description="Gestion personal" icon={CheckCircle} title="Completadas" tone="lime" value={dashboard.completed_tasks} />
      <KpiCard description="Asignadas" icon={ShieldAlert} title="Incidencias" tone="slate" value={dashboard.assigned_incidents} />
    </div>
  );
}
