import { Badge } from "@/components/ui/badge";
import type { SurveyStatus } from "@/types/survey";

const labels: Record<SurveyStatus, string> = {
  DRAFT: "Borrador",
  ACTIVE: "Activa",
  CLOSED: "Cerrada",
  ARCHIVED: "Archivada"
};

export function SurveyStatusBadge({ status }: { status: SurveyStatus | string }) {
  const tone = status === "ACTIVE" ? "success" : status === "CLOSED" || status === "ARCHIVED" ? "neutral" : "warning";
  return <Badge tone={tone}>{labels[status as SurveyStatus] ?? status}</Badge>;
}
