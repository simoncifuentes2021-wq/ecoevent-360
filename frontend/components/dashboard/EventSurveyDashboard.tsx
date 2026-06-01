import { MessageSquare, Star, Users } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import type { EventDashboard } from "@/types/dashboard";

export function EventSurveyDashboard({ dashboard }: { dashboard: EventDashboard }) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <KpiCard description="Importadas" icon={Users} title="Respuestas" value={dashboard.survey.total_responses} />
      <KpiCard description="Nota general" icon={Star} title="Satisfaccion" tone="lime" value={dashboard.survey.average_rating ? dashboard.survey.average_rating.toFixed(1) : "0.0"} />
      <KpiCard description="Mayor frecuencia" icon={MessageSquare} title="Problema principal" value={dashboard.survey.main_problem || "Sin dato"} />
    </div>
  );
}
