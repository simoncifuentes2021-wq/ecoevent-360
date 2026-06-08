import type { EventStatus } from "@/types/event";

export const eventStatusLabels: Record<EventStatus, string> = {
  QUOTE: "Cotizacion",
  PLANNING: "Planificacion",
  IN_PROGRESS: "En curso",
  FINISHED: "Finalizado",
  REPORT_DELIVERED: "Reporte entregado",
  CANCELLED: "Cancelado"
};

const commonStatusLabels: Record<string, string> = {
  ACTIVE: "Activo",
  INACTIVE: "Inactivo",
  COMPLETED: "Completado",
  PENDING: "Pendiente",
  OBSERVED: "Observado",
  CLOSED: "Cerrado"
};

export function statusLabel(status: string) {
  return eventStatusLabels[status as EventStatus] ?? commonStatusLabels[status] ?? status.replaceAll("_", " ");
}
