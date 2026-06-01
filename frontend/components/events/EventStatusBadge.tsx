import { Badge } from "@/components/ui/badge";
import type { EventStatus } from "@/types/event";

const labels: Record<EventStatus, string> = {
  QUOTE: "Cotizacion",
  PLANNING: "Planificacion",
  IN_PROGRESS: "En curso",
  FINISHED: "Finalizado",
  REPORT_DELIVERED: "Reporte entregado",
  CANCELLED: "Cancelado"
};

export function EventStatusBadge({ status }: { status: EventStatus }) {
  const tone =
    status === "FINISHED" || status === "REPORT_DELIVERED"
      ? "success"
      : status === "CANCELLED"
        ? "danger"
        : status === "IN_PROGRESS"
          ? "default"
          : "warning";

  return <Badge tone={tone}>{labels[status]}</Badge>;
}
