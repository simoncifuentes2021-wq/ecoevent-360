import { MessageSquare, Star, Users } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { EventDashboard } from "@/types/dashboard";

export function EventSurveyDashboard({ dashboard }: { dashboard: EventDashboard }) {
  if (dashboard.survey.total_responses <= 0) return null;

  return (
    <Card className="border-slate-200/80 shadow-[0_12px_32px_-24px_rgba(15,23,42,0.45)]">
      <CardHeader className="bg-slate-50/70"><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-700">Experiencia</p><h3 className="mt-1 text-base font-bold text-slate-950">Lectura de formularios</h3></CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-3">
        <KpiCard description="Respuestas recibidas" icon={Users} title="Respuestas" value={dashboard.survey.total_responses} />
        {dashboard.survey.average_rating > 0 ? <KpiCard description="Nota general" icon={Star} title="Satisfacción" tone="lime" value={dashboard.survey.average_rating.toFixed(1)} /> : null}
        {dashboard.survey.main_problem && dashboard.survey.main_problem !== "Sin dato" ? <KpiCard description="Mayor frecuencia" icon={MessageSquare} title="Problema principal" value={dashboard.survey.main_problem} /> : null}
      </CardContent>
    </Card>
  );
}
