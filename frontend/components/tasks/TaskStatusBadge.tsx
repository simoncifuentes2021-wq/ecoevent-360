import { Badge } from "@/components/ui/badge";
import type { TaskStatus } from "@/types/task";

const labels: Record<TaskStatus, string> = {
  PENDING: "Pendiente",
  IN_PROGRESS: "En progreso",
  COMPLETED: "Completada",
  OBSERVED: "Observada",
  CANCELLED: "Cancelada"
};

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const tone = status === "COMPLETED" ? "success" : status === "CANCELLED" ? "danger" : status === "PENDING" ? "warning" : "neutral";
  return <Badge tone={tone}>{labels[status] || status}</Badge>;
}
