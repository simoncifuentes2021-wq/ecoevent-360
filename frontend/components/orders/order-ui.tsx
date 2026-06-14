import type { OrderEvidenceStage, OrderItemStageStatus, OrderStatus } from "@/types/order";

export const orderStatusLabels: Record<OrderStatus, string> = {
  DRAFT: "Borrador",
  REQUESTED: "Solicitado",
  APPROVED: "Aprobado",
  PREPARING: "Preparando",
  LOADED: "Cargado",
  IN_TRANSIT: "En traslado",
  DELIVERED: "Entregado",
  RETURN_IN_PROGRESS: "Retorno",
  RETURNED: "Retornado",
  CLOSED: "Cerrado",
  CANCELLED: "Cancelado"
};

export const stageLabels: Record<OrderEvidenceStage, string> = {
  LOAD: "Carga",
  DELIVERY: "Entrega",
  RETURN: "Retorno"
};

export const itemStageLabels: Record<OrderItemStageStatus, string> = {
  PENDING: "Pendiente",
  COMPLETED: "Completado",
  OBSERVED: "Observado"
};

export function money(value?: string | number | null) {
  return Number(value ?? 0).toLocaleString("es-CL", { style: "currency", currency: "CLP", maximumFractionDigits: 0 });
}

export function numberValue(value?: string | number | null) {
  return Number(value ?? 0).toLocaleString("es-CL");
}

export function dateValue(value?: string | null) {
  return value ? new Date(value).toLocaleDateString("es-CL") : "Sin fecha";
}

export function OrderStatusBadge({ status }: { status: OrderStatus }) {
  const tone = status === "CANCELLED" ? "bg-rose-50 text-rose-700" : status === "CLOSED" || status === "RETURNED" ? "bg-slate-100 text-slate-700" : "bg-emerald-50 text-emerald-700";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${tone}`}>{orderStatusLabels[status]}</span>;
}

export function ItemStageBadge({ status }: { status: OrderItemStageStatus }) {
  const tone = status === "COMPLETED" ? "bg-emerald-50 text-emerald-700" : status === "OBSERVED" ? "bg-amber-50 text-amber-700" : "bg-slate-100 text-slate-600";
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold ${tone}`}>{itemStageLabels[status]}</span>;
}

export function ProgressLine({ label, value, count }: { label: string; value: number; count?: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs font-semibold text-slate-600">
        <span>{label}</span>
        <span>{count || `${value}%`}</span>
      </div>
      <div className="h-2 rounded-full bg-slate-100">
        <div className="h-2 rounded-full bg-emerald-600" style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  );
}
