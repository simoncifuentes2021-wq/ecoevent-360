import { Badge } from "@/components/ui/badge";
import type { IncidentStatus } from "@/types/incident";

const labels: Record<IncidentStatus, string> = {
  REPORTED: "Reportada",
  ASSIGNED: "Asignada",
  IN_PROGRESS: "En progreso",
  RESOLVED: "Resuelta",
  CLOSED: "Cerrada",
  CANCELLED: "Cancelada"
};

export function IncidentStatusBadge({ status }: { status: IncidentStatus }) {
  const tone = status === "RESOLVED" || status === "CLOSED" ? "success" : status === "CANCELLED" ? "danger" : status === "REPORTED" ? "warning" : "neutral";
  return <Badge tone={tone}>{labels[status] || status}</Badge>;
}
