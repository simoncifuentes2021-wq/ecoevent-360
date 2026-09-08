"use client";

import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  CalendarDays,
  Check,
  CircleDot,
  MapPin,
  Package2,
  UserRound,
  Warehouse
} from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { LogisticsOrder, LogisticsOrderStatus } from "@/types/logistics-order";

export const logisticsStatusLabels: Record<LogisticsOrderStatus, string> = {
  REQUESTED: "Solicitado",
  ASSIGNED: "Asignado",
  STOCK_REVIEW: "Revisión de stock",
  RESERVED: "Stock reservado",
  INSUFFICIENT_STOCK: "Stock insuficiente",
  IN_PREPARATION: "En preparación",
  LOADED: "Carga completa",
  OUT_OF_WAREHOUSE: "En ruta",
  DELIVERED: "Entregado",
  PARTIALLY_DELIVERED: "Entrega parcial",
  OUTCOME_PENDING: "Resultado pendiente",
  OUTCOME_RECORDED: "Resultado registrado",
  WITH_DIFFERENCES: "Con diferencias",
  CLOSED: "Cerrado",
  OBSERVED: "Observado",
  CANCELLED: "Cancelado"
};

const phases = ["Solicitud", "Stock", "Preparación", "Entrega", "Cierre"];

const phaseByStatus: Record<LogisticsOrderStatus, number> = {
  REQUESTED: 0,
  ASSIGNED: 0,
  STOCK_REVIEW: 1,
  INSUFFICIENT_STOCK: 1,
  RESERVED: 1,
  IN_PREPARATION: 2,
  LOADED: 2,
  OUT_OF_WAREHOUSE: 3,
  DELIVERED: 3,
  PARTIALLY_DELIVERED: 3,
  OUTCOME_PENDING: 4,
  OUTCOME_RECORDED: 4,
  WITH_DIFFERENCES: 4,
  CLOSED: 4,
  OBSERVED: 4,
  CANCELLED: 0
};

const statusHelp: Record<LogisticsOrderStatus, string> = {
  REQUESTED: "Pendiente de asignación y revisión.",
  ASSIGNED: "Listo para revisar disponibilidad.",
  STOCK_REVIEW: "Comprobando existencias en bodega.",
  RESERVED: "Existencias separadas para este pedido.",
  INSUFFICIENT_STOCK: "Requiere reposición o una compra.",
  IN_PREPARATION: "El equipo está preparando los productos.",
  LOADED: "Todo listo para confirmar la salida.",
  OUT_OF_WAREHOUSE: "Pedido despachado hacia el evento.",
  DELIVERED: "Entrega completada en terreno.",
  PARTIALLY_DELIVERED: "Quedan productos por entregar.",
  OUTCOME_PENDING: "Falta registrar el resultado del uso.",
  OUTCOME_RECORDED: "Listo para revisión y cierre.",
  WITH_DIFFERENCES: "Hay cantidades pendientes de explicar.",
  CLOSED: "Flujo logístico finalizado.",
  OBSERVED: "Requiere revisión del equipo.",
  CANCELLED: "Este pedido ya no está operativo."
};

export function LogisticsOrderStatusBadge({ status }: { status: LogisticsOrderStatus }) {
  const tone =
    status === "CANCELLED"
      ? "danger"
      : ["INSUFFICIENT_STOCK", "WITH_DIFFERENCES", "OBSERVED", "PARTIALLY_DELIVERED"].includes(status)
        ? "warning"
        : status === "CLOSED"
          ? "neutral"
          : "success";

  return <Badge tone={tone}>{logisticsStatusLabels[status]}</Badge>;
}

export function LogisticsOrderProgress({ status }: { status: LogisticsOrderStatus }) {
  const currentPhase = phaseByStatus[status];
  const isCancelled = status === "CANCELLED";

  return (
    <div>
      <div className="grid grid-cols-5 gap-1.5" aria-label={`Etapa actual: ${logisticsStatusLabels[status]}`}>
        {phases.map((phase, index) => {
          const complete = !isCancelled && (status === "CLOSED" || index < currentPhase);
          const current = !isCancelled && status !== "CLOSED" && index === currentPhase;
          return (
            <div className="min-w-0" key={phase}>
              <div
                className={cn(
                  "flex h-2 rounded-full bg-slate-200 transition-colors",
                  complete && "bg-emerald-500",
                  current && "bg-emerald-300",
                  isCancelled && index === 0 && "bg-rose-300"
                )}
              />
              <p className={cn("mt-1.5 truncate text-[10px] font-semibold text-slate-400 sm:text-xs", (complete || current) && "text-emerald-700")}>
                {phase}
              </p>
            </div>
          );
        })}
      </div>
      <p className={cn("mt-2 text-xs text-slate-500", isCancelled && "text-rose-600")}>{statusHelp[status]}</p>
    </div>
  );
}

export function LogisticsOrdersOverview({
  orders,
  loading,
  error,
  onRetry,
  hrefFor,
  emptyTitle = "Sin pedidos logísticos",
  emptyDescription = "Los pedidos aparecerán aquí cuando sean creados.",
  showOperator = true
}: {
  orders: LogisticsOrder[];
  loading: boolean;
  error: string | null;
  onRetry?: () => void | Promise<void>;
  hrefFor: (order: LogisticsOrder) => string;
  emptyTitle?: string;
  emptyDescription?: string;
  showOperator?: boolean;
}) {
  if (loading) {
    return (
      <div className="grid gap-4 lg:grid-cols-2" aria-label="Cargando pedidos logísticos">
        {[0, 1, 2, 3].map((item) => (
          <div className="h-72 animate-pulse rounded-2xl border bg-white" key={item} />
        ))}
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={onRetry} />;

  if (orders.length === 0) {
    return (
      <EmptyState
        icon={<Package2 className="h-7 w-7" />}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {orders.map((order) => (
        <article
          className="group overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-lg"
          key={order.id}
        >
          <div className="border-b border-slate-100 bg-gradient-to-br from-white via-white to-emerald-50/70 p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase tracking-[0.12em] text-emerald-700">
                  <CircleDot className="h-3.5 w-3.5" /> Pedido logístico
                </p>
                <Link className="text-lg font-bold text-slate-950 outline-none hover:text-emerald-700 focus-visible:underline" href={hrefFor(order)}>
                  {order.title}
                </Link>
                <p className="mt-1 truncate text-sm text-slate-500">{order.event?.name || "Evento no disponible"}</p>
              </div>
              <LogisticsOrderStatusBadge status={order.status} />
            </div>
          </div>

          <div className="space-y-4 p-5">
            <LogisticsOrderProgress status={order.status} />

            <div className="grid gap-2 text-sm sm:grid-cols-2">
              <OrderFact icon={Warehouse} label="Bodega" value={order.warehouse?.name || "Sin bodega"} />
              {showOperator ? (
                <OrderFact icon={UserRound} label="Operador" value={order.assigned_operator?.full_name || "Sin asignar"} />
              ) : (
                <OrderFact icon={MapPin} label="Entrega" value={order.delivery_zone || "Por definir"} />
              )}
              <OrderFact icon={Package2} label="Productos" value={`${order.items.length} ${order.items.length === 1 ? "producto" : "productos"}`} />
              <OrderFact icon={CalendarDays} label="Creado" value={formatDate(order.created_at)} />
            </div>

            <div className="flex items-end justify-between gap-3 border-t border-slate-100 pt-4">
              <div>
                <p className="text-xs font-medium text-slate-500">Total estimado</p>
                <p className="text-lg font-extrabold text-slate-950">{money(order.total_estimated_amount)}</p>
              </div>
              <Link
                className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white transition group-hover:bg-emerald-700"
                href={hrefFor(order)}
              >
                Abrir pedido <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function OrderFact({ icon: Icon, label, value }: { icon: typeof Check; label: string; value: string }) {
  return (
    <div className="flex min-w-0 items-center gap-2.5 rounded-lg bg-slate-50 px-3 py-2.5">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-white text-emerald-700 shadow-sm">
        <Icon className="h-4 w-4" />
      </span>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{label}</p>
        <p className="truncate font-semibold text-slate-700" title={value}>{value}</p>
      </div>
    </div>
  );
}

export function LogisticsAttentionNote({ count }: { count: number }) {
  if (count === 0) return null;
  return (
    <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
      <p><span className="font-bold">{count} {count === 1 ? "pedido requiere" : "pedidos requieren"} atención.</span> Revisa faltantes o diferencias antes de continuar.</p>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", {
    timeZone: "America/Santiago",
    day: "2-digit",
    month: "short",
    year: "numeric"
  }).format(new Date(value));
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}
