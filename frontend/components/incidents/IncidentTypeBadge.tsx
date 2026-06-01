import { Badge } from "@/components/ui/badge";
import type { IncidentType } from "@/types/incident";

const labels: Record<IncidentType, string> = {
  SANITARY: "Sanitaria",
  WASTE: "Residuos",
  CLEANING: "Limpieza",
  ENVIRONMENTAL: "Ambiental",
  SAFETY: "Seguridad",
  OTHER: "Otra"
};

export function IncidentTypeBadge({ type }: { type?: IncidentType | null }) {
  return <Badge tone="neutral">{type ? labels[type] : "Otra"}</Badge>;
}
