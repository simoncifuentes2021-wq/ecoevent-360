import { MessageSquare, Recycle, Star, ThumbsUp, Users } from "lucide-react";

import { KpiCard } from "@/components/dashboard/KpiCard";
import { formatSurveyRate, formatSurveyRating, getTopSurveyProblem } from "@/lib/normalizers/survey";
import type { SurveySummary } from "@/types/survey";

export function SurveySummaryCards({ summary }: { summary: SurveySummary }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
      <KpiCard description="CSV importado" icon={Users} title="Respuestas" value={summary.total_responses} />
      <KpiCard description="Nota general" icon={Star} title="Promedio" tone="lime" value={formatSurveyRating(summary.average_rating)} />
      <KpiCard description="Recomendaria el evento" icon={ThumbsUp} title="Recomendacion" tone="blue" value={formatSurveyRate(summary.recommendation_rate)} />
      <KpiCard description="Separacion de residuos" icon={Recycle} title="Reciclaje" tone="slate" value={formatSurveyRate(summary.recycling_action_rate)} />
      <KpiCard description="Mayor frecuencia" icon={MessageSquare} title="Problema principal" value={getTopSurveyProblem(summary)} />
    </div>
  );
}
