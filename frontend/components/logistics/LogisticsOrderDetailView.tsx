"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  Boxes,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  MapPin,
  PackageCheck,
  RefreshCcw,
  RotateCcw,
  ShoppingCart,
  Truck,
  UserRound,
  Warehouse as WarehouseIcon
} from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { LogisticsEvidenceGallery } from "@/components/logistics/LogisticsEvidenceGallery";
import { LogisticsEvidenceUploader } from "@/components/logistics/LogisticsEvidenceUploader";
import { LogisticsOrderStatusBadge } from "@/components/logistics/LogisticsOrdersOverview";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  checkLogisticsOrderStock,
  closeLogisticsOrder,
  createPartialDispatchRequest,
  confirmLogisticsOrderDelivery,
  confirmLogisticsOrderOutcome,
  deliverLogisticsOrderItem,
  dispatchLogisticsOrder,
  getLogisticsOrder,
  getLogisticsOrderStockAvailability,
  getPartialDispatchRequest,
  loadLogisticsOrderItem,
  markAllLogisticsOrderConsumablesConsumed,
  reserveLogisticsOrderStock,
  approvePartialDispatchRequest,
  rejectPartialDispatchRequest,
  registerLogisticsOrderItemOutcome,
  startLogisticsOrderPreparation,
  transferStockToLogisticsOrder,
  unreserveLogisticsOrderStock
} from "@/lib/api/logistics-orders";
import { createPurchaseRequestFromOrder, getPurchaseRequestsForOrder } from "@/lib/api/purchase-requests";
import type {
  LogisticsOrder,
  LogisticsOrderAvailability,
  LogisticsOrderItemAvailability,
  LogisticsPartialDispatchRequest,
  LogisticsOrderStatus,
  LogisticsOrderStockCheck,
  LogisticsOrderWarehouseAvailability
} from "@/types/logistics-order";
import type { PurchaseDeliveryMode, PurchaseRequest, PurchaseRequestStatus } from "@/types/purchase-request";
import type { UserRole } from "@/types/roles";

const purchaseStatusLabels: Record<PurchaseRequestStatus, string> = {
  REQUESTED: "Solicitada",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  PURCHASED: "Comprada",
  PARTIALLY_RECEIVED: "Recepcion parcial",
  RECEIVED: "Recibida",
  DELIVERED_DIRECT_TO_EVENT: "Directo al evento",
  CANCELLED: "Cancelada"
};

const purchaseModeLabels: Record<PurchaseDeliveryMode, string> = {
  TO_WAREHOUSE: "A bodega",
  DIRECT_TO_EVENT: "Directo al evento"
};

const workflowSteps = [
  { title: "Resumen", shortTitle: "Resumen", description: "Revisa los datos del pedido", icon: ClipboardList },
  { title: "Stock", shortTitle: "Stock", description: "Revisa y reserva productos", icon: Boxes },
  { title: "Preparación", shortTitle: "Preparar", description: "Carga y despacha desde bodega", icon: PackageCheck },
  { title: "Entrega", shortTitle: "Entregar", description: "Registra la entrega en terreno", icon: Truck },
  { title: "Resultados", shortTitle: "Resultados", description: "Explica consumo y devoluciones", icon: RotateCcw },
  { title: "Cierre", shortTitle: "Cerrar", description: "Finaliza el pedido", icon: CheckCircle2 }
] as const;

function currentWorkflowStep(status: LogisticsOrderStatus) {
  if (["REQUESTED", "ASSIGNED", "STOCK_REVIEW", "INSUFFICIENT_STOCK", "OBSERVED", "CANCELLED"].includes(status)) return 1;
  if (["RESERVED", "IN_PREPARATION", "LOADED"].includes(status)) return 2;
  if (status === "OUT_OF_WAREHOUSE") return 3;
  if (["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING"].includes(status)) return 4;
  return 5;
}

function nextActionFor(status: LogisticsOrderStatus) {
  const actions: Record<LogisticsOrderStatus, { eyebrow: string; title: string; description: string }> = {
    REQUESTED: { eyebrow: "Antes de comenzar", title: "Asigna el pedido", description: "El pedido debe tener bodega y operador antes de revisar su disponibilidad." },
    ASSIGNED: { eyebrow: "Tu siguiente acción", title: "Revisa el stock", description: "Comprueba las existencias de la bodega y luego reserva todos los productos." },
    STOCK_REVIEW: { eyebrow: "Tu siguiente acción", title: "Reserva los productos", description: "Verifica las cantidades disponibles y confirma la reserva del pedido." },
    RESERVED: { eyebrow: "Tu siguiente acción", title: "Inicia la preparación", description: "Comienza la carga y registra cada producto preparado para salir." },
    INSUFFICIENT_STOCK: { eyebrow: "Requiere atención", title: "Resuelve los productos faltantes", description: "Crea o gestiona una solicitud de compra y vuelve a revisar el stock." },
    IN_PREPARATION: { eyebrow: "Tu siguiente acción", title: "Completa la carga", description: "Registra la cantidad cargada de cada producto y adjunta su evidencia." },
    LOADED: { eyebrow: "Tu siguiente acción", title: "Confirma la salida de bodega", description: "Adjunta la evidencia obligatoria y confirma el despacho hacia el evento." },
    OUT_OF_WAREHOUSE: { eyebrow: "Tu siguiente acción", title: "Registra la entrega", description: "Indica cuánto recibió el evento, adjunta evidencia y confirma la entrega." },
    DELIVERED: { eyebrow: "Tu siguiente acción", title: "Registra los resultados", description: "Explica qué se consumió, devolvió, dañó, perdió o descartó." },
    PARTIALLY_DELIVERED: { eyebrow: "Tu siguiente acción", title: "Explica la entrega parcial", description: "Registra el resultado de lo entregado y deja documentadas las diferencias." },
    OUTCOME_PENDING: { eyebrow: "Tu siguiente acción", title: "Completa los resultados", description: "Aún hay productos cuyo resultado debe quedar explicado." },
    OUTCOME_RECORDED: { eyebrow: "Último paso", title: "Cierra el pedido", description: "Revisa el balance final, agrega una observación si corresponde y finaliza." },
    WITH_DIFFERENCES: { eyebrow: "Requiere atención", title: "Corrige las diferencias", description: "Revisa los productos pendientes de explicar antes de cerrar el pedido." },
    CLOSED: { eyebrow: "Proceso completado", title: "Pedido cerrado", description: "Todas las etapas operativas de este pedido ya fueron finalizadas." },
    OBSERVED: { eyebrow: "Requiere atención", title: "Revisa las observaciones", description: "Consulta los datos y corrige lo indicado antes de continuar." },
    CANCELLED: { eyebrow: "Proceso detenido", title: "Pedido cancelado", description: "Este pedido no tiene acciones operativas pendientes." }
  };
  return actions[status];
}

export function LogisticsOrderDetailView({
  orderId,
  backHref,
  roles
}: {
  orderId: string;
  backHref: string;
  roles: UserRole[];
}) {
  const [order, setOrder] = useState<LogisticsOrder | null>(null);
  const [stockCheck, setStockCheck] = useState<LogisticsOrderStockCheck | null>(null);
  const [stockAvailability, setStockAvailability] = useState<LogisticsOrderAvailability | null>(null);
  const [loading, setLoading] = useState(true);
  const [stockLoading, setStockLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);
  const [loadTarget, setLoadTarget] = useState<LogisticsOrder["items"][number] | null>(null);
  const [dispatchOpen, setDispatchOpen] = useState(false);
  const [deliveryTarget, setDeliveryTarget] = useState<LogisticsOrder["items"][number] | null>(null);
  const [deliveryConfirmOpen, setDeliveryConfirmOpen] = useState(false);
  const [outcomeTarget, setOutcomeTarget] = useState<LogisticsOrder["items"][number] | null>(null);
  const [outcomeConfirmOpen, setOutcomeConfirmOpen] = useState(false);
  const [bulkConsumeOpen, setBulkConsumeOpen] = useState(false);
  const [showCompletedOutcomes, setShowCompletedOutcomes] = useState(false);
  const [closureNotes, setClosureNotes] = useState("");
  const [purchaseRequests, setPurchaseRequests] = useState<PurchaseRequest[]>([]);
  const [partialDispatchRequest, setPartialDispatchRequest] = useState<LogisticsPartialDispatchRequest | null>(null);
  const [partialDispatchAction, setPartialDispatchAction] = useState<"request" | "approve" | "reject" | null>(null);
  const [purchaseOpen, setPurchaseOpen] = useState(false);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const [transferTarget, setTransferTarget] = useState<{
    item: LogisticsOrderItemAvailability;
    warehouse: LogisticsOrderWarehouseAvailability;
  } | null>(null);
  const [selectedStep, setSelectedStep] = useState<number | null>(null);
  const canReserve = roles.some((role) => ["SUPER_ADMIN", "ADMIN", "LOGISTICS_OPERATOR"].includes(role));
  const canOperate = canReserve;
  const canCreatePurchase = roles.some((role) => ["SUPER_ADMIN", "ADMIN", "SUPERVISOR", "LOGISTICS_OPERATOR"].includes(role));
  const canOpenAdminPurchases = roles.some((role) => ["SUPER_ADMIN", "ADMIN"].includes(role));
  const canReviewPartialDispatch = roles.some((role) => ["SUPER_ADMIN", "ADMIN", "SUPERVISOR"].includes(role));
  const activePurchaseRequests = useMemo(
    () => purchaseRequests.filter((purchase) => ["REQUESTED", "APPROVED", "PURCHASED", "PARTIALLY_RECEIVED"].includes(purchase.status)),
    [purchaseRequests]
  );
  const purchaseMissingRows = useMemo(() => {
    if (!order) return [];
    if (stockCheck?.items.length) {
      return stockCheck.items
        .filter((item) => Number(item.missing_quantity || 0) > 0)
        .map((item) => ({
          key: item.item_id,
          name: item.item_name_snapshot,
          quantity: item.missing_quantity,
          unit: order.items.find((orderItem) => orderItem.item_id === item.item_id)?.unit_snapshot || ""
        }));
    }
    return order.items
      .filter((item) => Number(item.quantity_missing || 0) > 0)
      .map((item) => ({
        key: item.id,
        name: item.item_name_snapshot,
        quantity: item.quantity_missing,
        unit: item.unit_snapshot || ""
      }));
  }, [order, stockCheck]);
  const consumablesToMark = useMemo(
    () =>
      order?.items.filter(
        (item) =>
          item.item_type_snapshot === "CONSUMABLE" &&
          Number(item.quantity_delivered || 0) > 0 &&
          (
            Number(item.quantity_consumed || 0) !== Number(item.quantity_delivered || 0) ||
            Number(item.quantity_returned || 0) > 0 ||
            Number(item.quantity_returned_damaged || 0) > 0 ||
            Number(item.quantity_lost || 0) > 0 ||
            Number(item.quantity_discarded || 0) > 0
          )
      ) || [],
    [order]
  );
  const deliveredOutcomeItems = useMemo(
    () => order?.items.filter((item) => Number(item.quantity_delivered || 0) > 0) || [],
    [order]
  );
  const pendingOutcomeItems = useMemo(
    () => deliveredOutcomeItems.filter((item) => item.outcome_status !== "RECORDED" || outcomePending(item) > 0),
    [deliveredOutcomeItems]
  );
  const visibleOutcomeItems = showCompletedOutcomes ? deliveredOutcomeItems : pendingOutcomeItems;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setOrder(await getLogisticsOrder(orderId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el pedido.");
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  const loadStockCheck = useCallback(async () => {
    setStockLoading(true);
    setStockError(null);
    try {
      const [check, availability] = await Promise.all([
        checkLogisticsOrderStock(orderId),
        getLogisticsOrderStockAvailability(orderId)
      ]);
      setStockCheck(check);
      setStockAvailability(availability);
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos revisar el stock.");
    } finally {
      setStockLoading(false);
    }
  }, [orderId]);

  async function submitTransfer(quantityToTransfer: number, notes?: string | null) {
    if (!transferTarget) return;
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await transferStockToLogisticsOrder(orderId, {
        logistics_order_item_id: transferTarget.item.logistics_order_item_id,
        source_warehouse_id: transferTarget.warehouse.warehouse_id,
        quantity: quantityToTransfer,
        notes
      }));
      setTransferTarget(null);
      await loadStockCheck();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos transferir el stock.");
    } finally {
      setActionLoading(false);
    }
  }

  const loadPurchaseRequests = useCallback(async () => {
    setPurchaseError(null);
    try {
      const response = await getPurchaseRequestsForOrder(orderId, { page: 1, limit: 100 });
      setPurchaseRequests(response.items);
    } catch (err) {
      setPurchaseError(err instanceof Error ? err.message : "No pudimos cargar las compras asociadas.");
    }
  }, [orderId]);

  const loadPartialDispatchRequest = useCallback(async () => {
    try {
      setPartialDispatchRequest(await getPartialDispatchRequest(orderId));
    } catch {
      setPartialDispatchRequest(null);
    }
  }, [orderId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadPurchaseRequests();
    void loadPartialDispatchRequest();
  }, [loadPurchaseRequests, loadPartialDispatchRequest]);

  async function submitPartialDispatch(reasonOrNotes: string) {
    if (!partialDispatchAction) return;
    setActionLoading(true);
    setStockError(null);
    try {
      if (partialDispatchAction === "request") {
        setPartialDispatchRequest(await createPartialDispatchRequest(orderId, reasonOrNotes));
      } else if (partialDispatchRequest) {
        if (partialDispatchAction === "approve") {
          const result = await approvePartialDispatchRequest(partialDispatchRequest.id, reasonOrNotes || null);
          setOrder(result.dispatch_order);
          setPartialDispatchRequest(result.request);
          await loadStockCheck();
        } else {
          setPartialDispatchRequest(await rejectPartialDispatchRequest(partialDispatchRequest.id, reasonOrNotes || null));
        }
      }
      setPartialDispatchAction(null);
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos procesar el despacho parcial.");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitPurchaseRequest(payload: {
    title: string;
    delivery_mode: PurchaseDeliveryMode;
    warehouse_id?: string | null;
    notes?: string | null;
  }) {
    setActionLoading(true);
    setPurchaseError(null);
    try {
      await createPurchaseRequestFromOrder(orderId, payload);
      setPurchaseOpen(false);
      await loadPurchaseRequests();
    } catch (err) {
      setPurchaseError(err instanceof Error ? err.message : "No pudimos crear la solicitud de compra.");
    } finally {
      setActionLoading(false);
    }
  }

  async function reserveStock() {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await reserveLogisticsOrderStock(orderId));
      await loadStockCheck();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos reservar el stock.");
      await loadStockCheck();
      await load();
    } finally {
      setActionLoading(false);
    }
  }

  async function unreserveStock() {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await unreserveLogisticsOrderStock(orderId));
      await loadStockCheck();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos liberar la reserva.");
    } finally {
      setActionLoading(false);
    }
  }

  async function startPreparation() {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await startLogisticsOrderPreparation(orderId));
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos iniciar la preparacion.");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitLoad(itemId: string, quantityLoaded: number, notes?: string | null) {
    setActionLoading(true);
    setStockError(null);
    try {
      await loadLogisticsOrderItem(itemId, { quantity_loaded: quantityLoaded, notes });
      setLoadTarget(null);
      await load();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos registrar la carga.");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitDispatch(notes?: string | null) {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await dispatchLogisticsOrder(orderId, { dispatch_notes: notes }));
      setDispatchOpen(false);
      await loadStockCheck();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos confirmar la salida de bodega.");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitDelivery(itemId: string, quantityDelivered: number, notes?: string | null) {
    setActionLoading(true);
    setStockError(null);
    try {
      await deliverLogisticsOrderItem(itemId, { quantity_delivered: quantityDelivered, notes });
      setDeliveryTarget(null);
      await load();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos registrar la entrega.");
    } finally {
      setActionLoading(false);
    }
  }

  async function confirmDelivery(notes?: string | null) {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await confirmLogisticsOrderDelivery(orderId, { delivery_notes: notes }));
      setDeliveryConfirmOpen(false);
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos confirmar la entrega en terreno.");
    } finally {
      setActionLoading(false);
    }
  }

  async function submitOutcome(
    itemId: string,
    payload: {
      quantity_consumed: number;
      quantity_returned: number;
      quantity_returned_damaged: number;
      quantity_lost: number;
      quantity_discarded: number;
      notes?: string | null;
    }
  ) {
    setActionLoading(true);
    setStockError(null);
    try {
      await registerLogisticsOrderItemOutcome(itemId, payload);
      setOutcomeTarget(null);
      await load();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos registrar el resultado.");
    } finally {
      setActionLoading(false);
    }
  }

  async function confirmOutcome(notes?: string | null) {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await confirmLogisticsOrderOutcome(orderId, { outcome_notes: notes }));
      setOutcomeConfirmOpen(false);
      await loadStockCheck();
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos confirmar los resultados.");
    } finally {
      setActionLoading(false);
    }
  }

  async function closeOrder() {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await closeLogisticsOrder(orderId, { closure_notes: closureNotes || null }));
      setClosureNotes("");
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos cerrar el pedido.");
    } finally {
      setActionLoading(false);
    }
  }

  async function markConsumablesConsumed() {
    setActionLoading(true);
    setStockError(null);
    try {
      setOrder(await markAllLogisticsOrderConsumablesConsumed(orderId));
      setBulkConsumeOpen(false);
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos registrar los consumibles.");
      setBulkConsumeOpen(false);
    } finally {
      setActionLoading(false);
    }
  }

  function openOutcome(item: LogisticsOrder["items"][number]) {
    setStockError(null);
    setOutcomeTarget(item);
  }

  const recommendedStep = order ? currentWorkflowStep(order.status) : 0;
  const visibleStep = selectedStep ?? recommendedStep;
  const nextAction = order ? nextActionFor(order.status) : null;

  function selectStep(step: number) {
    if (step <= recommendedStep || step === 0) setSelectedStep(step);
  }

  return (
    <RoleGuard roles={roles}>
      <div className="space-y-6">
        <Link href={backHref}>
          <Button type="button" variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Volver
          </Button>
        </Link>
        {loading ? <LoadingState /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {order ? (
          <>
            <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
              <div className="bg-gradient-to-br from-slate-950 via-slate-900 to-emerald-950 px-5 py-6 text-white sm:px-7">
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                  <div className="min-w-0">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">Pedido logístico</p>
                    <h1 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">{order.title}</h1>
                    <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold text-slate-200">
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5">
                        <MapPin className="h-3.5 w-3.5 text-emerald-300" /> {order.event?.name || "Evento no disponible"}
                      </span>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1.5">
                        <WarehouseIcon className="h-3.5 w-3.5 text-emerald-300" /> {order.warehouse?.name || "Sin bodega"}
                      </span>
                    </div>
                  </div>
                  <div className="shrink-0 rounded-lg bg-white p-1.5 shadow-sm">
                    <LogisticsOrderStatusBadge status={order.status} />
                  </div>
                </div>
              </div>
            </section>
            <WorkflowGuide
              currentStep={recommendedStep}
              selectedStep={visibleStep}
              status={order.status}
              onSelect={selectStep}
            />
            {nextAction ? (
              <section className="relative overflow-hidden rounded-2xl border border-emerald-200 bg-emerald-50 px-5 py-5 shadow-sm sm:px-6">
                <div className="absolute inset-y-0 left-0 w-1.5 bg-emerald-500" />
                <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-emerald-600 text-white">
                      <ChevronRight className="h-5 w-5" />
                    </span>
                    <div>
                      <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-emerald-700">{nextAction.eyebrow}</p>
                      <h2 className="mt-1 text-xl font-extrabold text-slate-950">{nextAction.title}</h2>
                      <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-700">{nextAction.description}</p>
                    </div>
                  </div>
                  {visibleStep !== recommendedStep ? (
                    <Button className="shrink-0" type="button" onClick={() => setSelectedStep(null)}>
                      Ir al paso actual
                    </Button>
                  ) : null}
                </div>
              </section>
            ) : null}
            {visibleStep === 0 ? (
              <>
            <div className="grid gap-4 md:grid-cols-3">
              <Metric icon={Boxes} label="Total estimado" value={money(order.total_estimated_amount)} />
              <Metric icon={MapPin} label="Zona/lugar entrega" value={order.delivery_zone || "Por definir"} />
              <Metric icon={UserRound} label="Operador" value={order.assigned_operator?.full_name || "Sin asignar"} />
            </div>
            {order.delivery_notes ? (
              <Card>
                <CardContent>
                  <p className="text-sm text-muted-foreground">Observaciones</p>
                  <p className="mt-1 font-semibold">{order.delivery_notes}</p>
                </CardContent>
              </Card>
            ) : null}
            <Card>
              <CardContent>
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <h2 className="text-lg font-bold text-slate-950">Productos solicitados</h2>
                    <p className="text-sm text-muted-foreground">Detalle original y valorización del pedido.</p>
                  </div>
                  <Badge tone="neutral">{order.items.length} {order.items.length === 1 ? "producto" : "productos"}</Badge>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[720px] text-left text-sm">
                    <thead className="border-b text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4">Producto</th>
                        <th className="py-3 pr-4">Tipo</th>
                        <th className="py-3 pr-4">Unidad</th>
                        <th className="py-3 pr-4">Cantidad</th>
                        <th className="py-3 pr-4">Precio usado</th>
                        <th className="py-3 pr-4">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {order.items.map((item) => (
                        <tr className="border-b last:border-0" key={item.id}>
                          <td className="py-3 pr-4 font-semibold">{item.item_name_snapshot}</td>
                          <td className="py-3 pr-4">{item.item_type_snapshot}</td>
                          <td className="py-3 pr-4">{item.unit_snapshot || "-"}</td>
                          <td className="py-3 pr-4">{quantity(item.quantity_requested)}</td>
                          <td className="py-3 pr-4">{money(item.unit_price_snapshot)}</td>
                          <td className="py-3 pr-4">{money(item.total_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
            <LogisticsEvidenceGallery logisticsOrderId={order.id} orderItems={order.items} />
              </>
            ) : null}
            {visibleStep === 1 ? (
              <>
            <Card>
              <CardContent>
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                  <div>
                    <h2 className="text-lg font-bold">Disponibilidad de stock</h2>
                    <p className="text-sm text-muted-foreground">
                      Solo se considera stock disponible en la bodega del pedido: {order.warehouse?.name || "-"}.
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button disabled={stockLoading || actionLoading} onClick={loadStockCheck} type="button" variant="secondary">
                      <RefreshCcw className="h-4 w-4" />
                      Revisar stock
                    </Button>
                    {canReserve && ["ASSIGNED", "STOCK_REVIEW", "INSUFFICIENT_STOCK"].includes(order.status) ? (
                      <Button
                        disabled={actionLoading || stockLoading}
                        onClick={reserveStock}
                        type="button"
                      >
                        {stockCheck && !stockCheck.can_reserve_all ? "Reservar disponible" : "Reservar stock"}
                      </Button>
                    ) : null}
                    {canReserve && order.status === "RESERVED" ? (
                      <Button disabled={actionLoading} onClick={unreserveStock} type="button" variant="secondary">
                        Liberar reserva
                      </Button>
                    ) : null}
                  </div>
                </div>
                {stockError ? <p className="mt-3 text-sm font-semibold text-amber-700">{stockError}</p> : null}
                {order.status === "RESERVED" ? <p className="mt-3 text-sm font-semibold text-emerald-700">Stock reservado.</p> : null}
                {order.status === "INSUFFICIENT_STOCK" || (stockCheck && !stockCheck.can_reserve_all) ? (
                  <p className="mt-3 text-sm font-semibold text-amber-700">
                    Puedes reservar ahora lo disponible y crear una compra solo por el faltante.
                  </p>
                ) : null}
                {stockLoading ? <LoadingState /> : null}
                <div className="mt-4 overflow-x-auto">
                  <table className="w-full min-w-[980px] text-left text-sm">
                    <thead className="border-b text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="py-3 pr-4">Producto</th>
                        <th className="py-3 pr-4">Solicitado</th>
                        <th className="py-3 pr-4">Reservado</th>
                        <th className="py-3 pr-4">Stock fisico</th>
                        <th className="py-3 pr-4">Ya reservado en bodega</th>
                        <th className="py-3 pr-4">Danado</th>
                        <th className="py-3 pr-4">Disponible</th>
                        <th className="py-3 pr-4">Faltante</th>
                        <th className="py-3 pr-4">Estado</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(stockCheck?.items || order.items.map(itemToStockRow)).map((item) => (
                        <tr className="border-b last:border-0" key={item.item_id}>
                          <td className="py-3 pr-4 font-semibold">{item.item_name_snapshot}</td>
                          <td className="py-3 pr-4">{quantity(item.quantity_requested)}</td>
                          <td className="py-3 pr-4">{quantity(item.quantity_reserved)}</td>
                          <td className="py-3 pr-4">{quantity(item.quantity_on_hand)}</td>
                          <td className="py-3 pr-4">{quantity(item.quantity_reserved_in_stock)}</td>
                          <td className="py-3 pr-4">{quantity(item.quantity_damaged)}</td>
                          <td className="py-3 pr-4">{quantity(item.available_quantity)}</td>
                          <td className="py-3 pr-4">{quantity(item.missing_quantity)}</td>
                          <td className="py-3 pr-4">
                            <Badge tone={stockTone(item.can_reserve, Number(item.missing_quantity || 0))}>
                              {stockLabel(item.can_reserve, Number(item.missing_quantity || 0), Number(item.quantity_reserved || 0))}
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
            {stockAvailability ? (
              <Card>
                <CardContent>
                  <div className="flex items-start gap-3">
                    <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-blue-50 text-blue-700">
                      <WarehouseIcon className="h-5 w-5" />
                    </span>
                    <div>
                      <h2 className="text-lg font-bold">Stock en otras bodegas</h2>
                      <p className="text-sm text-muted-foreground">
                        Si falta stock en {stockAvailability.warehouse_name}, puedes traerlo desde otra bodega antes de comprar.
                      </p>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-4">
                    {stockAvailability.items.map((item) => (
                      <div className="rounded-xl border p-4" key={item.logistics_order_item_id}>
                        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                          <div>
                            <h3 className="font-bold text-slate-950">{item.item_name_snapshot}</h3>
                            <p className="text-sm text-muted-foreground">
                              Faltante actual: {quantity(item.quantity_missing)} {item.unit_snapshot || ""}
                            </p>
                          </div>
                          <Badge tone={Number(item.quantity_missing || 0) > 0 ? "warning" : "success"}>
                            {Number(item.quantity_missing || 0) > 0 ? "Buscar abastecimiento" : "Cubierto en destino"}
                          </Badge>
                        </div>
                        <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                          {item.warehouses.map((warehouse) => (
                            <div
                              className={`rounded-lg border p-3 ${warehouse.is_order_warehouse ? "border-emerald-200 bg-emerald-50" : "bg-slate-50"}`}
                              key={warehouse.warehouse_id}
                            >
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <p className="text-sm font-bold">{warehouse.warehouse_name}</p>
                                  <p className="mt-1 text-xs text-muted-foreground">
                                    {warehouse.is_order_warehouse ? "Bodega del pedido" : "Bodega alternativa"}
                                  </p>
                                </div>
                                <span className={`text-lg font-extrabold ${Number(warehouse.available_quantity || 0) > 0 ? "text-emerald-700" : "text-slate-400"}`}>
                                  {quantity(warehouse.available_quantity)}
                                </span>
                              </div>
                              {!warehouse.is_order_warehouse && Number(warehouse.available_quantity || 0) > 0 ? (
                                warehouse.can_transfer ? (
                                  <Button
                                    className="mt-3 w-full"
                                    disabled={actionLoading || Number(item.quantity_missing || 0) <= 0}
                                    onClick={() => setTransferTarget({ item, warehouse })}
                                    size="sm"
                                    type="button"
                                    variant="secondary"
                                  >
                                    Transferir a {stockAvailability.warehouse_name}
                                  </Button>
                                ) : (
                                  <p className="mt-3 text-xs font-semibold text-amber-700">
                                    Disponible, pero necesitas permisos en ambas bodegas.
                                  </p>
                                )
                              ) : null}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ) : null}
            {order.status === "INSUFFICIENT_STOCK" && order.items.some((item) => Number(item.quantity_reserved || 0) > 0) ? (
              <Card className="border-blue-200 bg-blue-50/40">
                <CardContent>
                  <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                    <div>
                      <h2 className="text-lg font-bold">¿Necesitas despachar solamente lo disponible?</h2>
                      <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
                        Con aprobación, este pedido conservará lo reservado y quedará listo para preparar. El faltante se moverá a un nuevo pedido vinculado.
                      </p>
                      {partialDispatchRequest ? (
                        <div className="mt-3 rounded-lg border bg-white p-3 text-sm">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge tone={partialDispatchRequest.status === "APPROVED" ? "success" : partialDispatchRequest.status === "REJECTED" ? "danger" : "warning"}>
                              {partialDispatchRequest.status === "PENDING" ? "Esperando aprobación" : partialDispatchRequest.status === "APPROVED" ? "Aprobada" : "Rechazada"}
                            </Badge>
                            <span className="font-semibold">Motivo: {partialDispatchRequest.reason}</span>
                          </div>
                          {partialDispatchRequest.review_notes ? <p className="mt-2 text-muted-foreground">Revisión: {partialDispatchRequest.review_notes}</p> : null}
                          {partialDispatchRequest.pending_order_id ? (
                            <Link className="mt-2 inline-block font-bold text-emerald-700 underline" href={`${backHref}/${partialDispatchRequest.pending_order_id}`}>
                              Abrir pedido pendiente
                            </Link>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {(!partialDispatchRequest || partialDispatchRequest.status === "REJECTED") && activePurchaseRequests.length === 0 ? (
                        <Button disabled={actionLoading} onClick={() => setPartialDispatchAction("request")} type="button" variant="secondary">
                          Solicitar despacho disponible
                        </Button>
                      ) : null}
                      {partialDispatchRequest?.status === "PENDING" && canReviewPartialDispatch ? (
                        <>
                          <Button disabled={actionLoading} onClick={() => setPartialDispatchAction("reject")} type="button" variant="secondary">Rechazar</Button>
                          <Button disabled={actionLoading} onClick={() => setPartialDispatchAction("approve")} type="button">Aprobar y dividir pedido</Button>
                        </>
                      ) : null}
                    </div>
                  </div>
                  {activePurchaseRequests.length > 0 ? (
                    <p className="mt-3 text-sm font-semibold text-amber-700">Primero debes finalizar o cancelar la compra activa.</p>
                  ) : null}
                </CardContent>
              </Card>
            ) : null}
            {(order.status === "INSUFFICIENT_STOCK" || purchaseMissingRows.length > 0 || purchaseRequests.length > 0) ? (
              <Card>
                <CardContent>
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                    <div>
                      <h2 className="text-lg font-bold">Compra por falta de stock</h2>
                      <p className="text-sm text-muted-foreground">
                        Crea una solicitud con los productos faltantes del pedido logistico.
                      </p>
                    </div>
                    {canCreatePurchase && purchaseMissingRows.length > 0 && activePurchaseRequests.length === 0 ? (
                      <Button disabled={actionLoading} type="button" onClick={() => setPurchaseOpen(true)}>
                        <ShoppingCart className="h-4 w-4" />
                        Crear solicitud de compra
                      </Button>
                    ) : null}
                  </div>
                  {purchaseError ? <p className="mt-3 text-sm font-semibold text-amber-700">{purchaseError}</p> : null}
                  {activePurchaseRequests.length > 0 ? (
                    <p className="mt-3 text-sm font-semibold text-amber-700">
                      Este pedido ya tiene una solicitud de compra activa. Finalizala, rechazala o cancelala antes de crear otra.
                    </p>
                  ) : null}
                  {purchaseRequests.some((purchase) => purchase.status === "RECEIVED" && purchase.delivery_mode === "TO_WAREHOUSE") ? (
                    <p className="mt-3 text-sm font-semibold text-emerald-700">
                      Stock recibido en bodega. Puedes volver a revisar y reservar stock para este pedido.
                    </p>
                  ) : null}
                  {purchaseRequests.some((purchase) => purchase.status === "DELIVERED_DIRECT_TO_EVENT") ? (
                    <p className="mt-3 text-sm font-semibold text-amber-700">
                      Hay compras entregadas directo al evento. Esas compras no aumentan el stock de bodega.
                    </p>
                  ) : null}
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <div className="rounded-lg border p-3">
                      <h3 className="text-sm font-bold">Faltantes actuales</h3>
                      <div className="mt-3 divide-y">
                        {purchaseMissingRows.map((item) => (
                          <div className="flex items-center justify-between gap-3 py-2 text-sm" key={item.key}>
                            <span className="font-semibold">{item.name}</span>
                            <span>{quantity(item.quantity)} {item.unit}</span>
                          </div>
                        ))}
                        {purchaseMissingRows.length === 0 ? (
                          <p className="py-2 text-sm text-muted-foreground">No hay faltantes pendientes.</p>
                        ) : null}
                      </div>
                    </div>
                    <div className="rounded-lg border p-3">
                      <h3 className="text-sm font-bold">Solicitudes asociadas</h3>
                      <div className="mt-3 divide-y">
                        {purchaseRequests.map((purchase) => (
                          <div className="grid gap-2 py-2 text-sm sm:grid-cols-[1fr_auto_auto]" key={purchase.id}>
                            <div>
                              <p className="font-semibold">{purchase.title}</p>
                              <p className="text-xs text-muted-foreground">
                                {purchaseModeLabels[purchase.delivery_mode]} - {money(purchase.total_estimated_amount)}
                              </p>
                            </div>
                            <Badge tone={purchaseStatusTone(purchase.status)}>{purchaseStatusLabels[purchase.status]}</Badge>
                            {canOpenAdminPurchases ? (
                              <Link href="/admin/stock/compras">
                                <Button size="sm" type="button" variant="secondary">Ver compras</Button>
                              </Link>
                            ) : null}
                          </div>
                        ))}
                        {purchaseRequests.length === 0 ? (
                          <p className="py-2 text-sm text-muted-foreground">Aun no hay solicitudes de compra para este pedido.</p>
                        ) : null}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : null}
              </>
            ) : null}
            {visibleStep === 2 && ["RESERVED", "IN_PREPARATION", "LOADED", "OUT_OF_WAREHOUSE", "DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "OUTCOME_RECORDED", "WITH_DIFFERENCES", "CLOSED"].includes(order.status) ? (
              <Card>
                <CardContent>
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                    <div>
                      <h2 className="text-lg font-bold">Preparacion y salida</h2>
                      <p className="text-sm text-muted-foreground">Registra la carga de productos reservados antes de confirmar salida de bodega.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {canOperate && order.status === "RESERVED" ? (
                        <Button disabled={actionLoading} onClick={startPreparation} type="button">
                          Iniciar preparacion
                        </Button>
                      ) : null}
                      {canOperate && order.status === "LOADED" ? (
                        <Button disabled={actionLoading} onClick={() => setDispatchOpen(true)} type="button">
                          Confirmar salida de bodega
                        </Button>
                      ) : null}
                    </div>
                  </div>
                  {order.status === "OUT_OF_WAREHOUSE" ? (
                    <p className="mt-3 text-sm font-semibold text-emerald-700">
                      Pedido salio de bodega. Proxima etapa: entrega en terreno.
                    </p>
                  ) : null}
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[760px] text-left text-sm">
                      <thead className="border-b text-xs uppercase text-muted-foreground">
                        <tr>
                          <th className="py-3 pr-4">Producto</th>
                          <th className="py-3 pr-4">Reservado</th>
                          <th className="py-3 pr-4">Cargado</th>
                          <th className="py-3 pr-4">Unidad</th>
                          <th className="py-3 pr-4">Estado preparacion</th>
                          <th className="py-3 pr-4">Accion</th>
                        </tr>
                      </thead>
                      <tbody>
                        {order.items.map((item) => (
                          <tr className="border-b last:border-0" key={item.id}>
                            <td className="py-3 pr-4 font-semibold">{item.item_name_snapshot}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_reserved)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_loaded)}</td>
                            <td className="py-3 pr-4">{item.unit_snapshot || "-"}</td>
                            <td className="py-3 pr-4">
                              <Badge tone={item.preparation_status === "LOADED" ? "success" : item.preparation_status === "PARTIALLY_LOADED" ? "warning" : "neutral"}>
                                {preparationLabel(item.preparation_status)}
                              </Badge>
                            </td>
                            <td className="py-3 pr-4">
                              {canOperate && ["IN_PREPARATION", "LOADED"].includes(order.status) ? (
                                <Button size="sm" type="button" variant="secondary" onClick={() => setLoadTarget(item)}>
                                  Registrar carga
                                </Button>
                              ) : (
                                "-"
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <LogisticsEvidenceUploader
                      logisticsOrderId={order.id}
                      stage="LOGISTICS_LOADING"
                      title="Evidencias de preparacion/carga"
                    />
                    <LogisticsEvidenceUploader
                      logisticsOrderId={order.id}
                      required
                      stage="LOGISTICS_DISPATCH"
                      title="Evidencias de salida de bodega"
                    />
                  </div>
                </CardContent>
              </Card>
            ) : null}
            {visibleStep === 3 && ["OUT_OF_WAREHOUSE", "DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "OUTCOME_RECORDED", "WITH_DIFFERENCES", "CLOSED"].includes(order.status) ? (
              <Card>
                <CardContent>
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                    <div>
                      <h2 className="text-lg font-bold">Entrega en terreno</h2>
                      <p className="text-sm text-muted-foreground">
                        Registra cuanto se entrego efectivamente en el punto del evento.
                      </p>
                    </div>
                    {canOperate && order.status === "OUT_OF_WAREHOUSE" ? (
                      <Button
                        disabled={actionLoading || !order.items.some((item) => Number(item.quantity_delivered || 0) > 0)}
                        onClick={() => setDeliveryConfirmOpen(true)}
                        type="button"
                      >
                        Confirmar entrega en terreno
                      </Button>
                    ) : null}
                  </div>
                  {order.status === "DELIVERED" || order.status === "PARTIALLY_DELIVERED" ? (
                    <p className="mt-3 text-sm font-semibold text-emerald-700">
                      Entrega registrada. Proxima etapa: consumo, sobrantes, retorno, dano o perdida.
                    </p>
                  ) : null}
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[760px] text-left text-sm">
                      <thead className="border-b text-xs uppercase text-muted-foreground">
                        <tr>
                          <th className="py-3 pr-4">Producto</th>
                          <th className="py-3 pr-4">Despachado</th>
                          <th className="py-3 pr-4">Entregado</th>
                          <th className="py-3 pr-4">Unidad</th>
                          <th className="py-3 pr-4">Estado entrega</th>
                          <th className="py-3 pr-4">Accion</th>
                        </tr>
                      </thead>
                      <tbody>
                        {order.items.map((item) => (
                          <tr className="border-b last:border-0" key={item.id}>
                            <td className="py-3 pr-4 font-semibold">{item.item_name_snapshot}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_dispatched)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_delivered)}</td>
                            <td className="py-3 pr-4">{item.unit_snapshot || "-"}</td>
                            <td className="py-3 pr-4">
                              <Badge tone={item.delivery_status === "DELIVERED" ? "success" : item.delivery_status === "PARTIALLY_DELIVERED" ? "warning" : "neutral"}>
                                {deliveryLabel(item.delivery_status)}
                              </Badge>
                            </td>
                            <td className="py-3 pr-4">
                              {canOperate && order.status === "OUT_OF_WAREHOUSE" ? (
                                <Button size="sm" type="button" variant="secondary" onClick={() => setDeliveryTarget(item)}>
                                  Registrar entrega
                                </Button>
                              ) : (
                                "-"
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-4">
                    <LogisticsEvidenceUploader
                      logisticsOrderId={order.id}
                      required
                      stage="LOGISTICS_DELIVERY"
                      title="Evidencias de entrega en terreno"
                    />
                  </div>
                </CardContent>
              </Card>
            ) : null}
            {visibleStep === 4 && ["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "OUTCOME_RECORDED", "WITH_DIFFERENCES", "CLOSED"].includes(order.status) ? (
              <Card>
                <CardContent>
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                    <div>
                      <h2 className="text-lg font-bold">Resultado de productos</h2>
                      <p className="text-sm text-muted-foreground">
                        Registra consumo, sobrantes, retorno usable, retorno danado, perdida o descarte.
                      </p>
                    </div>
                    {canOperate && ["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "WITH_DIFFERENCES"].includes(order.status) ? (
                      <Button
                        disabled={actionLoading || deliveredOutcomeItems.length === 0}
                        onClick={() => setOutcomeConfirmOpen(true)}
                        type="button"
                      >
                        {pendingOutcomeItems.length > 0 ? "Confirmar con pendientes" : "Confirmar resultados"}
                      </Button>
                    ) : null}
                  </div>
                  {stockError ? (
                    <p className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">
                      {stockError}
                    </p>
                  ) : null}
                  {order.status === "OUTCOME_RECORDED" || order.status === "WITH_DIFFERENCES" ? (
                    <p className="mt-3 text-sm font-semibold text-emerald-700">
                      Resultados registrados. Proxima etapa: cierre operativo del pedido.
                    </p>
                  ) : null}
                  <div className="mt-5 grid gap-3 sm:grid-cols-3">
                    <OutcomeProgressMetric label="Productos entregados" value={deliveredOutcomeItems.length} tone="neutral" />
                    <OutcomeProgressMetric label="Resultados completos" value={deliveredOutcomeItems.length - pendingOutcomeItems.length} tone="success" />
                    <OutcomeProgressMetric label="Necesitan revisión" value={pendingOutcomeItems.length} tone={pendingOutcomeItems.length > 0 ? "warning" : "success"} />
                  </div>
                  <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                    <div
                      className="h-full rounded-full bg-emerald-500 transition-all"
                      style={{
                        width: `${deliveredOutcomeItems.length > 0 ? ((deliveredOutcomeItems.length - pendingOutcomeItems.length) / deliveredOutcomeItems.length) * 100 : 0}%`
                      }}
                    />
                  </div>
                  {canOperate && consumablesToMark.length > 0 && ["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "WITH_DIFFERENCES"].includes(order.status) ? (
                    <div className="mt-5 flex flex-col justify-between gap-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4 sm:flex-row sm:items-center">
                      <div>
                        <p className="font-bold text-emerald-950">¿Los consumibles se utilizaron completamente?</p>
                        <p className="mt-1 text-sm text-emerald-800">
                          Resuelve {consumablesToMark.length} {consumablesToMark.length === 1 ? "producto" : "productos"} de una vez. Después puedes editar cualquier excepción.
                        </p>
                      </div>
                      <Button className="shrink-0" disabled={actionLoading} onClick={() => setBulkConsumeOpen(true)} type="button">
                        <CheckCircle2 className="h-4 w-4" />
                        Sí, marcar todos
                      </Button>
                    </div>
                  ) : null}
                  <div className="mt-6 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                    <div>
                      <h3 className="font-bold text-slate-950">
                        {pendingOutcomeItems.length > 0 ? "Productos que debes revisar" : "Resultados completados"}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {pendingOutcomeItems.length > 0
                          ? "Completa solo los productos que todavía tienen cantidades pendientes."
                          : "Todos los productos entregados ya tienen un resultado."}
                      </p>
                    </div>
                    {deliveredOutcomeItems.length > pendingOutcomeItems.length ? (
                      <Button type="button" variant="secondary" onClick={() => setShowCompletedOutcomes((current) => !current)}>
                        {showCompletedOutcomes ? "Ocultar completados" : "Ver todos los productos"}
                      </Button>
                    ) : null}
                  </div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {visibleOutcomeItems.map((item) => (
                      <OutcomeProductCard
                        canEdit={canOperate && ["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "WITH_DIFFERENCES"].includes(order.status)}
                        item={item}
                        key={item.id}
                        onEdit={() => openOutcome(item)}
                      />
                    ))}
                    {visibleOutcomeItems.length === 0 ? (
                      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5 text-sm font-semibold text-emerald-800 lg:col-span-2">
                        No quedan productos pendientes. Ya puedes confirmar los resultados del pedido.
                      </div>
                    ) : null}
                  </div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    {order.items
                      .filter((item) => Number(item.quantity_delivered || 0) > 0)
                      .map((item) => (
                        <div className="space-y-3" key={item.id}>
                          <p className="text-sm font-bold">{item.item_name_snapshot}</p>
                          {Number(item.quantity_returned || 0) > 0 ? (
                            <LogisticsEvidenceUploader
                              logisticsOrderItemId={item.id}
                              stage="LOGISTICS_RETURN"
                              title="Evidencia de retorno usable"
                            />
                          ) : null}
                          <LogisticsEvidenceUploader
                            logisticsOrderItemId={item.id}
                            required={Number(item.quantity_returned_damaged || 0) > 0}
                            stage="LOGISTICS_DAMAGED_RETURN"
                            title="Evidencia de producto danado"
                          />
                          <LogisticsEvidenceUploader
                            logisticsOrderItemId={item.id}
                            required={Number(item.quantity_lost || 0) > 0}
                            stage="LOGISTICS_LOSS"
                            title="Evidencia de perdida"
                          />
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            ) : null}
            {visibleStep === 5 && ["OUTCOME_RECORDED", "WITH_DIFFERENCES", "CLOSED"].includes(order.status) ? (
              <Card>
                <CardContent>
                  <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
                    <div>
                      <h2 className="text-lg font-bold">Cierre operativo</h2>
                      <p className="text-sm text-muted-foreground">
                        Cierra el pedido cuando todos los productos esten explicados.
                      </p>
                    </div>
                    {order.status === "CLOSED" ? <Badge tone="success">Pedido cerrado</Badge> : null}
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-3 lg:grid-cols-6">
                    <ClosureMetric label="Productos entregados" value={quantity(sumOrder(order, "quantity_delivered"))} />
                    <ClosureMetric label="Consumidos/asignados" value={quantity(sumOrder(order, "quantity_consumed"))} />
                    <ClosureMetric label="Devueltos usables" value={quantity(sumOrder(order, "quantity_returned"))} />
                    <ClosureMetric label="Devueltos danados" value={quantity(sumOrder(order, "quantity_returned_damaged"))} />
                    <ClosureMetric label="Perdidos" value={quantity(sumOrder(order, "quantity_lost"))} />
                    <ClosureMetric label="Descartados" value={quantity(sumOrder(order, "quantity_discarded"))} />
                  </div>
                  <div className="mt-4 rounded-lg border bg-slate-50 p-3 text-sm">
                    Pendiente por explicar: <span className="font-semibold">{quantity(totalPending(order))}</span>
                  </div>
                  {order.status === "WITH_DIFFERENCES" ? (
                    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
                      <p className="font-semibold">No puedes cerrar este pedido porque existen cantidades pendientes por explicar.</p>
                      <ul className="mt-2 space-y-1">
                        {order.items.filter((item) => outcomePending(item) > 0).map((item) => (
                          <li key={item.id}>
                            {item.item_name_snapshot}: {quantity(item.quantity_delivered)} entregadas, {quantity(outcomeUsed(item))} explicadas, {quantity(outcomePending(item))} pendientes.
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {order.status === "CLOSED" ? (
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <ClosureMetric label="Cerrado por" value={order.closer?.full_name || order.closer?.email || order.closed_by || "-"} />
                      <ClosureMetric label="Fecha de cierre" value={order.closed_at ? new Date(order.closed_at).toLocaleString("es-CL", { timeZone: "America/Santiago" }) : "-"} />
                      <ClosureMetric label="Observacion de cierre" value={order.closure_notes || "-"} />
                    </div>
                  ) : null}
                  {canOperate && order.status === "OUTCOME_RECORDED" ? (
                    <div className="mt-4 space-y-3">
                      <label className="grid gap-2 text-sm font-semibold">
                        Observacion de cierre
                        <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={closureNotes} onChange={(event) => setClosureNotes(event.target.value)} />
                      </label>
                      <div className="flex justify-end">
                        <Button disabled={actionLoading || totalPending(order) > 0} onClick={closeOrder} type="button">
                          {actionLoading ? "Cerrando..." : "Cerrar pedido"}
                        </Button>
                      </div>
                    </div>
                  ) : null}
                  <div className="mt-4">
                    <LogisticsEvidenceUploader
                      logisticsOrderId={order.id}
                      stage="LOGISTICS_CLOSURE"
                      title="Evidencia opcional de cierre"
                    />
                  </div>
                </CardContent>
              </Card>
            ) : null}
            <StageNavigation
              currentStep={recommendedStep}
              selectedStep={visibleStep}
              onSelect={selectStep}
              onCurrent={() => setSelectedStep(null)}
            />
            {purchaseOpen ? (
              <PurchaseRequestModal
                order={order}
                stockCheck={stockCheck}
                saving={actionLoading}
                onClose={() => setPurchaseOpen(false)}
                onSubmit={submitPurchaseRequest}
              />
            ) : null}
            {loadTarget ? (
              <LoadItemModal
                item={loadTarget}
                saving={actionLoading}
                onClose={() => setLoadTarget(null)}
                onSubmit={submitLoad}
              />
            ) : null}
            {dispatchOpen ? (
              <DispatchModal
                order={order}
                saving={actionLoading}
                onClose={() => setDispatchOpen(false)}
                onSubmit={submitDispatch}
              />
            ) : null}
            {deliveryTarget ? (
              <DeliverItemModal
                item={deliveryTarget}
                saving={actionLoading}
                onClose={() => setDeliveryTarget(null)}
                onSubmit={submitDelivery}
              />
            ) : null}
            {deliveryConfirmOpen ? (
              <DeliveryConfirmModal
                order={order}
                saving={actionLoading}
                onClose={() => setDeliveryConfirmOpen(false)}
                onSubmit={confirmDelivery}
              />
            ) : null}
            {outcomeTarget ? (
              <OutcomeItemModal
                error={stockError}
                item={outcomeTarget}
                saving={actionLoading}
                onClose={() => setOutcomeTarget(null)}
                onSubmit={submitOutcome}
              />
            ) : null}
            {outcomeConfirmOpen ? (
              <OutcomeConfirmModal
                order={order}
                saving={actionLoading}
                onClose={() => setOutcomeConfirmOpen(false)}
                onSubmit={confirmOutcome}
              />
            ) : null}
            {transferTarget ? (
              <StockTransferModal
                destinationWarehouse={order.warehouse?.name || "Bodega del pedido"}
                item={transferTarget.item}
                saving={actionLoading}
                sourceWarehouse={transferTarget.warehouse}
                onClose={() => setTransferTarget(null)}
                onSubmit={submitTransfer}
              />
            ) : null}
            {partialDispatchAction ? (
              <PartialDispatchModal
                action={partialDispatchAction}
                saving={actionLoading}
                onClose={() => setPartialDispatchAction(null)}
                onSubmit={submitPartialDispatch}
              />
            ) : null}
            <ConfirmDialog
              open={bulkConsumeOpen}
              title="Marcar consumibles como consumidos"
              description={`Se marcarán ${consumablesToMark.length} ${consumablesToMark.length === 1 ? "producto consumible" : "productos consumibles"} con toda su cantidad entregada como consumida. Los retornables y consumibles parciales no se modificarán.`}
              confirmLabel="Marcar todos"
              loading={actionLoading}
              onClose={() => setBulkConsumeOpen(false)}
              onConfirm={() => void markConsumablesConsumed()}
            />
          </>
        ) : null}
      </div>
    </RoleGuard>
  );
}

function OutcomeProgressMetric({
  label,
  value,
  tone
}: {
  label: string;
  value: number;
  tone: "neutral" | "success" | "warning";
}) {
  const styles = {
    neutral: "border-slate-200 bg-slate-50 text-slate-950",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    warning: "border-amber-200 bg-amber-50 text-amber-800"
  };
  return (
    <div className={`rounded-xl border p-4 ${styles[tone]}`}>
      <p className="text-xs font-bold uppercase tracking-wide opacity-70">{label}</p>
      <p className="mt-1 text-2xl font-extrabold">{value}</p>
    </div>
  );
}

function OutcomeProductCard({
  item,
  canEdit,
  onEdit
}: {
  item: LogisticsOrder["items"][number];
  canEdit: boolean;
  onEdit: () => void;
}) {
  const pending = outcomePending(item);
  const complete = item.outcome_status === "RECORDED" && pending === 0;
  const results = [
    { label: "Consumido", value: Number(item.quantity_consumed || 0) },
    { label: "Devuelto", value: Number(item.quantity_returned || 0) },
    { label: "Dañado", value: Number(item.quantity_returned_damaged || 0) },
    { label: "Perdido", value: Number(item.quantity_lost || 0) },
    { label: "Descartado", value: Number(item.quantity_discarded || 0) }
  ].filter((result) => result.value > 0);

  return (
    <article className={`rounded-xl border p-4 ${complete ? "border-slate-200 bg-white" : "border-amber-200 bg-amber-50/40"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="font-bold text-slate-950">{item.item_name_snapshot}</h4>
          <p className="mt-1 text-xs font-semibold text-muted-foreground">
            {itemTypeLabel(item.item_type_snapshot)} · Entregado: {quantity(item.quantity_delivered)} {item.unit_snapshot || ""}
          </p>
        </div>
        <Badge tone={complete ? "success" : "warning"}>{complete ? "Listo" : `${quantity(pending)} pendiente`}</Badge>
      </div>
      <div className="mt-4 flex min-h-7 flex-wrap gap-2">
        {results.length > 0 ? results.map((result) => (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700" key={result.label}>
            {result.label}: {quantity(result.value)}
          </span>
        )) : (
          <span className="text-sm text-muted-foreground">Aún no se ha registrado ningún resultado.</span>
        )}
      </div>
      {canEdit ? (
        <Button className="mt-4 w-full" type="button" variant={complete ? "secondary" : "primary"} onClick={onEdit}>
          {complete ? "Editar resultado" : "Completar resultado"}
        </Button>
      ) : null}
    </article>
  );
}

function WorkflowGuide({
  currentStep,
  selectedStep,
  status,
  onSelect
}: {
  currentStep: number;
  selectedStep: number;
  status: LogisticsOrderStatus;
  onSelect: (step: number) => void;
}) {
  return (
    <Card className="overflow-hidden border-slate-200">
      <CardContent className="p-0">
        <div className="border-b bg-slate-50 px-5 py-4 sm:px-6">
          <div className="flex flex-col justify-between gap-1 sm:flex-row sm:items-center">
            <div>
              <h2 className="font-extrabold text-slate-950">Paso a paso del pedido</h2>
              <p className="text-sm text-muted-foreground">Trabaja una etapa a la vez. Las etapas futuras se habilitan al avanzar.</p>
            </div>
            <span className="text-sm font-bold text-emerald-700">
              {status === "CLOSED" ? "Proceso completo" : `Paso ${currentStep} de ${workflowSteps.length - 1}`}
            </span>
          </div>
        </div>
        <div className="overflow-x-auto px-4 py-4 sm:px-6">
          <ol className="flex min-w-[760px] items-start">
            {workflowSteps.map((step, index) => {
              const Icon = step.icon;
              const completed = index < currentStep || (status === "CLOSED" && index === currentStep);
              const current = index === currentStep && status !== "CLOSED";
              const selected = index === selectedStep;
              const enabled = index === 0 || index <= currentStep;
              return (
                <li className="relative flex flex-1 flex-col items-center px-1 text-center" key={step.title}>
                  {index > 0 ? (
                    <span className={`absolute right-1/2 top-5 h-0.5 w-full ${index <= currentStep ? "bg-emerald-500" : "bg-slate-200"}`} />
                  ) : null}
                  <button
                    aria-current={current ? "step" : undefined}
                    className="group relative z-10 flex w-full flex-col items-center disabled:cursor-not-allowed"
                    disabled={!enabled}
                    onClick={() => onSelect(index)}
                    type="button"
                  >
                    <span
                      className={`grid h-10 w-10 place-items-center rounded-full border-2 transition ${
                        selected
                          ? "border-emerald-600 bg-emerald-600 text-white ring-4 ring-emerald-100"
                          : completed
                            ? "border-emerald-500 bg-emerald-50 text-emerald-700"
                            : current
                              ? "border-emerald-500 bg-white text-emerald-700"
                              : "border-slate-200 bg-white text-slate-400"
                      }`}
                    >
                      {completed && !selected ? <Check className="h-4 w-4" /> : <Icon className="h-4 w-4" />}
                    </span>
                    <span className={`mt-2 text-xs font-bold ${enabled ? "text-slate-800" : "text-slate-400"}`}>{step.shortTitle}</span>
                    <span className="mt-0.5 max-w-[130px] text-[11px] leading-4 text-muted-foreground">{step.description}</span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      </CardContent>
    </Card>
  );
}

function StageNavigation({
  currentStep,
  selectedStep,
  onSelect,
  onCurrent
}: {
  currentStep: number;
  selectedStep: number;
  onSelect: (step: number) => void;
  onCurrent: () => void;
}) {
  const canGoBack = selectedStep > 0;
  const canGoForward = selectedStep < currentStep;

  return (
    <div className="sticky bottom-3 z-20 flex flex-col gap-3 rounded-2xl border border-slate-200 bg-white/95 p-3 shadow-lg backdrop-blur sm:flex-row sm:items-center sm:justify-between">
      <p className="px-1 text-sm text-slate-600">
        Viendo <span className="font-bold text-slate-950">{workflowSteps[selectedStep].title}</span>
      </p>
      <div className="flex flex-wrap gap-2">
        {selectedStep !== currentStep ? (
          <Button type="button" variant="secondary" onClick={onCurrent}>Ir al paso actual</Button>
        ) : null}
        <Button disabled={!canGoBack} type="button" variant="secondary" onClick={() => onSelect(selectedStep - 1)}>
          <ChevronLeft className="h-4 w-4" />
          Anterior
        </Button>
        <Button disabled={!canGoForward} type="button" onClick={() => onSelect(selectedStep + 1)}>
          Siguiente
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function Metric({ icon: Icon, label, value }: { icon: typeof Boxes; label: string; value: string }) {
  return (
    <Card className="border-slate-200">
      <CardContent className="flex items-center gap-3 p-4">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
          <p className="mt-0.5 truncate text-lg font-bold text-slate-950" title={value}>{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ClosureMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 break-words text-base font-bold">{value}</p>
    </div>
  );
}

function PartialDispatchModal({
  action,
  saving,
  onClose,
  onSubmit
}: {
  action: "request" | "approve" | "reject";
  saving: boolean;
  onClose: () => void;
  onSubmit: (text: string) => Promise<void>;
}) {
  const [text, setText] = useState("");
  const requesting = action === "request";
  const valid = requesting ? text.trim().length >= 5 : true;
  const titles = {
    request: "Solicitar despacho de lo disponible",
    approve: "Aprobar y dividir pedido",
    reject: "Rechazar despacho parcial"
  };
  return (
    <ModalShell title={titles[action]} description="La decisión quedará registrada en el pedido." onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void onSubmit(text.trim()); }}>
        <p className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
          {requesting
            ? "Un administrador o supervisor deberá aprobar. Lo reservado seguirá en este pedido y el faltante formará otro pedido vinculado."
            : action === "approve"
              ? "Se creará el pedido pendiente y este pedido quedará completamente reservado, listo para preparación."
              : "El pedido conservará su reserva parcial y podrá resolverse mediante transferencia o compra."}
        </p>
        <label className="grid gap-2 text-sm font-semibold">
          {requesting ? "Motivo obligatorio" : "Comentario de revisión (opcional)"}
          <textarea
            className="min-h-24 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            onChange={(event) => setText(event.target.value)}
            placeholder={requesting ? "Ej.: el evento comienza hoy y debemos enviar las unidades disponibles" : "Agrega una observación si corresponde"}
            value={text}
          />
        </label>
        {!valid ? <p className="text-sm font-semibold text-amber-700">Escribe un motivo de al menos 5 caracteres.</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} onClick={onClose} type="button" variant="secondary">Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Procesando..." : titles[action]}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function StockTransferModal({
  item,
  sourceWarehouse,
  destinationWarehouse,
  saving,
  onClose,
  onSubmit
}: {
  item: LogisticsOrderItemAvailability;
  sourceWarehouse: LogisticsOrderWarehouseAvailability;
  destinationWarehouse: string;
  saving: boolean;
  onClose: () => void;
  onSubmit: (quantityToTransfer: number, notes?: string | null) => Promise<void>;
}) {
  const maximum = Math.min(
    Number(item.quantity_missing || 0),
    Number(sourceWarehouse.available_quantity || 0)
  );
  const [amount, setAmount] = useState(String(maximum));
  const [notes, setNotes] = useState("");
  const numericAmount = Number(amount);
  const valid = Number.isInteger(numericAmount) && numericAmount > 0 && numericAmount <= maximum;

  return (
    <ModalShell
      title="Transferir stock entre bodegas"
      description={item.item_name_snapshot}
      onClose={onClose}
    >
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (valid) void onSubmit(numericAmount, notes || null);
        }}
      >
        <div className="grid gap-3 rounded-xl border bg-slate-50 p-4 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">Desde</p>
            <p className="mt-1 font-bold">{sourceWarehouse.warehouse_name}</p>
            <p className="text-sm text-muted-foreground">
              {quantity(sourceWarehouse.available_quantity)} disponibles
            </p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-muted-foreground">Hacia</p>
            <p className="mt-1 font-bold">{destinationWarehouse}</p>
            <p className="text-sm text-muted-foreground">
              Faltan {quantity(item.quantity_missing)} {item.unit_snapshot || ""}
            </p>
          </div>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Cantidad a transferir
          <Input
            max={maximum}
            min="1"
            onChange={(event) => setAmount(event.target.value)}
            step="1"
            type="number"
            value={amount}
          />
        </label>
        <p className="text-xs text-muted-foreground">
          Máximo permitido: {quantity(maximum)}. La transferencia quedará registrada como salida e ingreso de stock.
        </p>
        <label className="grid gap-2 text-sm font-semibold">
          Nota opcional
          <textarea
            className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            onChange={(event) => setNotes(event.target.value)}
            value={notes}
          />
        </label>
        {!valid ? (
          <p className="text-sm font-semibold text-amber-700">
            Ingresa una cantidad entera entre 1 y {quantity(maximum)}.
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} onClick={onClose} type="button" variant="secondary">Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">
            {saving ? "Transfiriendo..." : "Confirmar transferencia"}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}

function PurchaseRequestModal({
  order,
  stockCheck,
  saving,
  onClose,
  onSubmit
}: {
  order: LogisticsOrder;
  stockCheck: LogisticsOrderStockCheck | null;
  saving: boolean;
  onClose: () => void;
  onSubmit: (payload: {
    title: string;
    delivery_mode: PurchaseDeliveryMode;
    warehouse_id?: string | null;
    notes?: string | null;
  }) => Promise<void>;
  }) {
  const [title, setTitle] = useState(`Compra por faltantes - ${order.title}`);
  const [notes, setNotes] = useState("");
  const missingItems = stockCheck?.items.length
    ? stockCheck.items
        .filter((item) => Number(item.missing_quantity || 0) > 0)
        .map((item) => ({
          key: item.item_id,
          name: item.item_name_snapshot,
          quantity: item.missing_quantity,
          unit: order.items.find((orderItem) => orderItem.item_id === item.item_id)?.unit_snapshot || ""
        }))
    : order.items
        .filter((item) => Number(item.quantity_missing || 0) > 0)
        .map((item) => ({
          key: item.id,
          name: item.item_name_snapshot,
          quantity: item.quantity_missing,
          unit: item.unit_snapshot || ""
        }));
  const valid = title.trim().length > 0 && missingItems.length > 0 && Boolean(order.warehouse_id);

  return (
    <ModalShell title="Crear solicitud de compra" description={order.title} size="lg" onClose={onClose}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (!valid) return;
          void onSubmit({
            title: title.trim(),
            delivery_mode: "TO_WAREHOUSE",
            warehouse_id: order.warehouse_id,
            notes: notes || null
          });
        }}
      >
        <label className="grid gap-2 text-sm font-semibold">
          Titulo
          <Input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <div className="grid gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-4 md:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase text-emerald-700">Modo de entrega</p>
            <p className="mt-1 font-bold text-slate-950">Ingreso a bodega</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-emerald-700">Bodega destino</p>
            <p className="mt-1 font-bold text-slate-950">{order.warehouse?.name || "Bodega del pedido"}</p>
          </div>
          <p className="text-sm text-emerald-800 md:col-span-2">
            Al recibirse, estos productos aumentarán el stock de la misma bodega y podrán completar la reserva.
          </p>
        </div>
        <div className="rounded-lg border bg-slate-50 p-3">
          <p className="text-sm font-bold">Productos faltantes</p>
          <div className="mt-2 divide-y">
            {missingItems.map((item) => (
              <div className="flex items-center justify-between gap-3 py-2 text-sm" key={item.key}>
                <span className="font-semibold">{item.name}</span>
                <span>{quantity(item.quantity)} {item.unit}</span>
              </div>
            ))}
          </div>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Notas
          <textarea
            className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
          />
        </label>
        {!valid ? (
          <p className="text-sm font-semibold text-amber-700">Debes tener faltantes, titulo y una bodega asignada al pedido.</p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Creando..." : "Crear solicitud"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function purchaseStatusTone(status: PurchaseRequestStatus) {
  if (status === "REJECTED" || status === "CANCELLED") return "danger";
  if (status === "REQUESTED" || status === "PARTIALLY_RECEIVED") return "warning";
  return "success";
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}

function quantity(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL");
}

function itemToStockRow(item: LogisticsOrder["items"][number]) {
  return {
    item_id: item.id,
    item_name_snapshot: item.item_name_snapshot,
    quantity_requested: item.quantity_requested,
    quantity_reserved: item.quantity_reserved,
    quantity_on_hand: 0,
    quantity_reserved_in_stock: 0,
    quantity_damaged: 0,
    available_quantity: 0,
    missing_quantity: item.quantity_missing,
    can_reserve: item.reservation_status !== "INSUFFICIENT_STOCK"
  };
}

function stockTone(canReserve: boolean, missing: number) {
  if (missing > 0 || !canReserve) return "warning";
  return "success";
}

function stockLabel(canReserve: boolean, missing: number, reserved: number) {
  if (reserved > 0 && missing === 0) return "Reservado";
  if (missing > 0 || !canReserve) return "Insuficiente";
  return "Disponible";
}

function preparationLabel(status: string) {
  if (status === "LOADED") return "Cargado";
  if (status === "PARTIALLY_LOADED") return "Carga parcial";
  return "Pendiente";
}

function deliveryLabel(status: string) {
  if (status === "DELIVERED") return "Entregado";
  if (status === "PARTIALLY_DELIVERED") return "Entrega parcial";
  return "Pendiente";
}

function outcomeLabel(status: string) {
  if (status === "RECORDED") return "Registrado";
  if (status === "PARTIAL") return "Parcial";
  if (status === "WITH_DIFFERENCES") return "Con diferencias";
  return "Pendiente";
}

function itemTypeLabel(type: string) {
  if (type === "RETURNABLE") return "Retornable";
  if (type === "CONSUMABLE") return "Consumible";
  if (type === "PARTIAL_CONSUMABLE") return "Parcial";
  if (type === "DISPOSABLE") return "Desechable";
  return type;
}

function outcomeUsed(item: LogisticsOrder["items"][number]) {
  return (
    Number(item.quantity_consumed || 0) +
    Number(item.quantity_returned || 0) +
    Number(item.quantity_returned_damaged || 0) +
    Number(item.quantity_lost || 0) +
    Number(item.quantity_discarded || 0)
  );
}

function outcomePending(item: LogisticsOrder["items"][number]) {
  return Math.max(Number(item.quantity_delivered || 0) - outcomeUsed(item), 0);
}

function totalPending(order: LogisticsOrder) {
  return order.items.reduce((sum, item) => sum + outcomePending(item), 0);
}

function sumOrder(order: LogisticsOrder, field: keyof LogisticsOrder["items"][number]) {
  return order.items.reduce((sum, item) => sum + Number(item[field] || 0), 0);
}

function LoadItemModal({
  item,
  saving,
  onClose,
  onSubmit
}: {
  item: LogisticsOrder["items"][number];
  saving: boolean;
  onClose: () => void;
  onSubmit: (itemId: string, quantityLoaded: number, notes?: string | null) => Promise<void>;
}) {
  const [quantityLoaded, setQuantityLoaded] = useState(String(item.quantity_loaded || item.quantity_reserved || ""));
  const [notes, setNotes] = useState(item.notes || "");
  const loaded = Number(quantityLoaded);
  const reserved = Number(item.quantity_reserved || 0);
  const valid = Number.isInteger(loaded) && loaded > 0 && loaded <= reserved;

  return (
    <ModalShell title="Registrar carga" description={item.item_name_snapshot} onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void onSubmit(item.id, loaded, notes || null); }}>
        <div className="rounded-lg border bg-slate-50 p-3 text-sm">
          <p>Reservado: <span className="font-semibold">{quantity(item.quantity_reserved)}</span> {item.unit_snapshot || ""}</p>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Cantidad cargada
          <Input min={1} max={reserved} step="1" type="number" value={quantityLoaded} onChange={(event) => setQuantityLoaded(event.target.value)} />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Observacion
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        {!valid ? <p className="text-sm font-semibold text-amber-700">La cantidad debe ser un numero entero mayor a 0 y no superar lo reservado.</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Guardar carga"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function DeliverItemModal({
  item,
  saving,
  onClose,
  onSubmit
}: {
  item: LogisticsOrder["items"][number];
  saving: boolean;
  onClose: () => void;
  onSubmit: (itemId: string, quantityDelivered: number, notes?: string | null) => Promise<void>;
}) {
  const [quantityDelivered, setQuantityDelivered] = useState(String(item.quantity_delivered || item.quantity_dispatched || "0"));
  const [notes, setNotes] = useState(item.notes || "");
  const delivered = Number(quantityDelivered);
  const dispatched = Number(item.quantity_dispatched || 0);
  const valid = Number.isInteger(delivered) && delivered >= 0 && delivered <= dispatched;

  return (
    <ModalShell title="Registrar entrega" description={item.item_name_snapshot} onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); if (valid) void onSubmit(item.id, delivered, notes || null); }}>
        <div className="rounded-lg border bg-slate-50 p-3 text-sm">
          <p>Despachado: <span className="font-semibold">{quantity(item.quantity_dispatched)}</span> {item.unit_snapshot || ""}</p>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Cantidad entregada
          <Input min={0} max={dispatched} step="1" type="number" value={quantityDelivered} onChange={(event) => setQuantityDelivered(event.target.value)} />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Observacion
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        {!valid ? <p className="text-sm font-semibold text-amber-700">La cantidad entregada debe ser un numero entero, no puede ser negativa ni superar lo despachado.</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Guardar entrega"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function DeliveryConfirmModal({
  order,
  saving,
  onClose,
  onSubmit
}: {
  order: LogisticsOrder;
  saving: boolean;
  onClose: () => void;
  onSubmit: (notes?: string | null) => Promise<void>;
}) {
  const [notes, setNotes] = useState(order.delivery_notes || "");

  return (
    <ModalShell title="Confirmar entrega en terreno" description={order.event?.name || "Evento"} onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void onSubmit(notes || null); }}>
        <div className="rounded-lg border">
          <div className="divide-y">
            {order.items.map((item) => (
              <div className="flex items-center justify-between gap-3 p-3 text-sm" key={item.id}>
                <span className="font-semibold">{item.item_name_snapshot}</span>
                <span>{quantity(item.quantity_delivered)} / {quantity(item.quantity_dispatched)} {item.unit_snapshot || ""}</span>
              </div>
            ))}
          </div>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Observacion de entrega
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <p className="text-sm font-semibold text-emerald-700">No se modificara stock en esta etapa.</p>
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={saving} type="submit">{saving ? "Confirmando..." : "Confirmar entrega"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function OutcomeItemModal({
  error,
  item,
  saving,
  onClose,
  onSubmit
}: {
  error: string | null;
  item: LogisticsOrder["items"][number];
  saving: boolean;
  onClose: () => void;
  onSubmit: (
    itemId: string,
    payload: {
      quantity_consumed: number;
      quantity_returned: number;
      quantity_returned_damaged: number;
      quantity_lost: number;
      quantity_discarded: number;
      notes?: string | null;
    }
  ) => Promise<void>;
}) {
  const [consumed, setConsumed] = useState(String(item.quantity_consumed || "0"));
  const [returned, setReturned] = useState(String(item.quantity_returned || "0"));
  const [returnedDamaged, setReturnedDamaged] = useState(String(item.quantity_returned_damaged || "0"));
  const [lost, setLost] = useState(String(item.quantity_lost || "0"));
  const [discarded, setDiscarded] = useState(String(item.quantity_discarded || "0"));
  const [notes, setNotes] = useState(item.outcome_notes || "");
  const delivered = Number(item.quantity_delivered || 0);
  const values = [consumed, returned, returnedDamaged, lost, discarded].map((value) => Number(value || 0));
  const total = values.reduce((sum, value) => sum + value, 0);
  const pending = Math.max(delivered - total, 0);
  const valid =
    values.every((value) => Number.isInteger(value) && value >= 0) &&
    total <= delivered &&
    !(item.item_type_snapshot === "RETURNABLE" && values[0] > 0);

  function markAllConsumed() {
    setConsumed(String(delivered));
    setReturned("0");
    setReturnedDamaged("0");
    setLost("0");
    setDiscarded("0");
  }

  function markAllReturned() {
    setConsumed("0");
    setReturned(String(delivered));
    setReturnedDamaged("0");
    setLost("0");
    setDiscarded("0");
  }

  function markAllDiscarded() {
    setConsumed("0");
    setReturned("0");
    setReturnedDamaged("0");
    setLost("0");
    setDiscarded(String(delivered));
  }

  return (
    <ModalShell title="Registrar resultado" description={item.item_name_snapshot} onClose={onClose}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (!valid) return;
          void onSubmit(item.id, {
            quantity_consumed: values[0],
            quantity_returned: values[1],
            quantity_returned_damaged: values[2],
            quantity_lost: values[3],
            quantity_discarded: values[4],
            notes: notes || null
          });
        }}
      >
        <div className={`rounded-xl border p-4 ${pending === 0 ? "border-emerald-200 bg-emerald-50" : "border-amber-200 bg-amber-50"}`}>
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-bold uppercase tracking-wide text-muted-foreground">Cantidad entregada</p>
              <p className="mt-1 text-xl font-extrabold">{quantity(item.quantity_delivered)} {item.unit_snapshot || ""}</p>
            </div>
            <Badge tone={pending === 0 ? "success" : "warning"}>
              {pending === 0 ? "Resultado completo" : `${quantity(pending)} por explicar`}
            </Badge>
          </div>
        </div>
        <div className="rounded-xl border border-slate-200 p-4">
          <p className="text-sm font-bold text-slate-950">Elige el caso habitual</p>
          <p className="mt-1 text-sm text-muted-foreground">Esto completa los campos automáticamente. Si hubo una excepción, ajusta las cantidades debajo.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {item.item_type_snapshot !== "RETURNABLE" && item.item_type_snapshot !== "DISPOSABLE" ? (
              <Button type="button" variant="secondary" onClick={markAllConsumed}>Todo consumido</Button>
            ) : null}
            {item.item_type_snapshot !== "CONSUMABLE" && item.item_type_snapshot !== "DISPOSABLE" ? (
              <Button type="button" variant="secondary" onClick={markAllReturned}>Todo devuelto usable</Button>
            ) : null}
            {item.item_type_snapshot === "DISPOSABLE" ? (
              <Button type="button" variant="secondary" onClick={markAllDiscarded}>Todo descartado</Button>
            ) : null}
          </div>
        </div>
        {item.item_type_snapshot === "RETURNABLE" ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-800">
            Este producto debe volver, registrarse como danado o perdido.
          </p>
        ) : null}
        <div className="grid gap-3 md:grid-cols-2">
          <OutcomeInput label="Consumido/asignado" value={consumed} onChange={setConsumed} disabled={item.item_type_snapshot === "RETURNABLE"} />
          <OutcomeInput label="Devuelto usable" value={returned} onChange={setReturned} />
          <OutcomeInput label="Devuelto danado" value={returnedDamaged} onChange={setReturnedDamaged} />
          <OutcomeInput label="Perdido" value={lost} onChange={setLost} />
          <OutcomeInput label="Descartado" value={discarded} onChange={setDiscarded} />
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Observacion
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        {!valid ? (
          <p className="text-sm font-semibold text-amber-700">
            Las cantidades deben ser numeros enteros, no pueden ser negativas, la suma no puede superar lo entregado y los retornables no pueden marcarse como consumidos.
          </p>
        ) : null}
        {error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Guardar y volver"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function OutcomeInput({
  label,
  value,
  disabled,
  onChange
}: {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-2 text-sm font-semibold">
      {label}
      <Input disabled={disabled} min={0} step="1" type="number" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function OutcomeConfirmModal({
  order,
  saving,
  onClose,
  onSubmit
}: {
  order: LogisticsOrder;
  saving: boolean;
  onClose: () => void;
  onSubmit: (notes?: string | null) => Promise<void>;
}) {
  const [notes, setNotes] = useState(order.outcome_notes || "");
  const missing = order.items.reduce((sum, item) => sum + outcomePending(item), 0);

  return (
    <ModalShell title="Confirmar resultados del pedido" description={order.event?.name || "Evento"} onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void onSubmit(notes || null); }}>
        <div className="rounded-lg border bg-slate-50 p-3 text-sm">
          <p>Pendiente total por explicar: <span className="font-semibold">{quantity(missing)}</span></p>
          <p className="mt-1 text-muted-foreground">
            Si queda pendiente, el pedido quedara con diferencias. Esta accion no cierra el pedido.
          </p>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Observacion general
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={saving} type="submit">{saving ? "Confirmando..." : "Confirmar resultados"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function DispatchModal({
  order,
  saving,
  onClose,
  onSubmit
}: {
  order: LogisticsOrder;
  saving: boolean;
  onClose: () => void;
  onSubmit: (notes?: string | null) => Promise<void>;
}) {
  const [notes, setNotes] = useState(order.dispatch_notes || "");

  return (
    <ModalShell title="Confirmar salida de bodega" description={order.warehouse?.name || "Bodega origen"} onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void onSubmit(notes || null); }}>
        <div className="rounded-lg border">
          <div className="divide-y">
            {order.items.map((item) => (
              <div className="flex items-center justify-between gap-3 p-3 text-sm" key={item.id}>
                <span className="font-semibold">{item.item_name_snapshot}</span>
                <span>{quantity(item.quantity_loaded)} {item.unit_snapshot || ""}</span>
              </div>
            ))}
          </div>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Observacion de salida
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        <p className="text-sm font-semibold text-amber-700">Esta accion descuenta stock fisico y libera la reserva.</p>
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={saving} type="submit">{saving ? "Confirmando..." : "Confirmar salida"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}
