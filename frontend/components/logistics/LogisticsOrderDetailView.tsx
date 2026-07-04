"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, RefreshCcw, ShoppingCart } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { LogisticsEvidenceGallery } from "@/components/logistics/LogisticsEvidenceGallery";
import { LogisticsEvidenceUploader } from "@/components/logistics/LogisticsEvidenceUploader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  checkLogisticsOrderStock,
  closeLogisticsOrder,
  confirmLogisticsOrderDelivery,
  confirmLogisticsOrderOutcome,
  deliverLogisticsOrderItem,
  dispatchLogisticsOrder,
  getLogisticsOrder,
  loadLogisticsOrderItem,
  reserveLogisticsOrderStock,
  registerLogisticsOrderItemOutcome,
  startLogisticsOrderPreparation,
  unreserveLogisticsOrderStock
} from "@/lib/api/logistics-orders";
import { createPurchaseRequestFromOrder, getPurchaseRequestsForOrder } from "@/lib/api/purchase-requests";
import { getWarehouses } from "@/lib/api/warehouses";
import type { LogisticsOrder, LogisticsOrderStatus, LogisticsOrderStockCheck } from "@/types/logistics-order";
import type { PurchaseDeliveryMode, PurchaseRequest, PurchaseRequestStatus } from "@/types/purchase-request";
import type { UserRole } from "@/types/roles";
import type { Warehouse } from "@/types/warehouse";

const statusLabels: Record<LogisticsOrderStatus, string> = {
  REQUESTED: "Solicitado",
  ASSIGNED: "Asignado",
  STOCK_REVIEW: "Revision stock",
  RESERVED: "Stock reservado",
  INSUFFICIENT_STOCK: "Stock insuficiente",
  IN_PREPARATION: "En preparacion",
  LOADED: "Cargado",
  OUT_OF_WAREHOUSE: "Salida de bodega",
  DELIVERED: "Entregado",
  PARTIALLY_DELIVERED: "Entrega parcial",
  OUTCOME_PENDING: "Resultado pendiente",
  OUTCOME_RECORDED: "Resultados registrados",
  WITH_DIFFERENCES: "Con diferencias",
  CLOSED: "Cerrado",
  OBSERVED: "Observado",
  CANCELLED: "Cancelado"
};

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
  const [closureNotes, setClosureNotes] = useState("");
  const [purchaseRequests, setPurchaseRequests] = useState<PurchaseRequest[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [purchaseOpen, setPurchaseOpen] = useState(false);
  const [purchaseError, setPurchaseError] = useState<string | null>(null);
  const canReserve = roles.some((role) => ["SUPER_ADMIN", "ADMIN", "LOGISTICS_OPERATOR"].includes(role));
  const canOperate = canReserve;
  const canCreatePurchase = roles.some((role) => ["SUPER_ADMIN", "ADMIN", "SUPERVISOR", "LOGISTICS_OPERATOR"].includes(role));
  const canOpenAdminPurchases = roles.some((role) => ["SUPER_ADMIN", "ADMIN"].includes(role));
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
      setStockCheck(await checkLogisticsOrderStock(orderId));
    } catch (err) {
      setStockError(err instanceof Error ? err.message : "No pudimos revisar el stock.");
    } finally {
      setStockLoading(false);
    }
  }, [orderId]);

  const loadPurchaseRequests = useCallback(async () => {
    setPurchaseError(null);
    try {
      const response = await getPurchaseRequestsForOrder(orderId, { page: 1, limit: 100 });
      setPurchaseRequests(response.items);
    } catch (err) {
      setPurchaseError(err instanceof Error ? err.message : "No pudimos cargar las compras asociadas.");
    }
  }, [orderId]);

  const loadWarehouses = useCallback(async () => {
    try {
      const response = await getWarehouses({ page: 1, limit: 100 });
      setWarehouses(response.items.filter((warehouse) => warehouse.is_active));
    } catch {
      setWarehouses([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    void loadPurchaseRequests();
    void loadWarehouses();
  }, [loadPurchaseRequests, loadWarehouses]);

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
            <PageHeader
              title={order.title}
              description={`Evento: ${order.event?.name || "-"} - Bodega: ${order.warehouse?.name || "-"}`}
              actions={<StatusBadge status={order.status} />}
            />
            <div className="grid gap-4 md:grid-cols-3">
              <Metric label="Total estimado" value={money(order.total_estimated_amount)} />
              <Metric label="Zona/lugar entrega" value={order.delivery_zone || "-"} />
              <Metric label="Operador" value={order.assigned_operator?.full_name || "-"} />
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
                    {canReserve && (order.status === "ASSIGNED" || order.status === "INSUFFICIENT_STOCK") ? (
                      <Button
                        disabled={actionLoading || stockLoading || (stockCheck ? !stockCheck.can_reserve_all : false)}
                        onClick={reserveStock}
                        type="button"
                      >
                        Reservar stock
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
                    No hay stock suficiente en esta bodega para reservar este pedido.
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
            {["RESERVED", "IN_PREPARATION", "LOADED", "OUT_OF_WAREHOUSE"].includes(order.status) ? (
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
            {["OUT_OF_WAREHOUSE", "DELIVERED", "PARTIALLY_DELIVERED"].includes(order.status) ? (
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
            {["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "OUTCOME_RECORDED", "WITH_DIFFERENCES"].includes(order.status) ? (
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
                      <Button disabled={actionLoading} onClick={() => setOutcomeConfirmOpen(true)} type="button">
                        Confirmar resultados del pedido
                      </Button>
                    ) : null}
                  </div>
                  {order.status === "OUTCOME_RECORDED" || order.status === "WITH_DIFFERENCES" ? (
                    <p className="mt-3 text-sm font-semibold text-emerald-700">
                      Resultados registrados. Proxima etapa: cierre operativo del pedido.
                    </p>
                  ) : null}
                  <div className="mt-4 overflow-x-auto">
                    <table className="w-full min-w-[1120px] text-left text-sm">
                      <thead className="border-b text-xs uppercase text-muted-foreground">
                        <tr>
                          <th className="py-3 pr-4">Producto</th>
                          <th className="py-3 pr-4">Tipo</th>
                          <th className="py-3 pr-4">Entregado</th>
                          <th className="py-3 pr-4">Consumido/asignado</th>
                          <th className="py-3 pr-4">Devuelto usable</th>
                          <th className="py-3 pr-4">Devuelto danado</th>
                          <th className="py-3 pr-4">Perdido</th>
                          <th className="py-3 pr-4">Descartado</th>
                          <th className="py-3 pr-4">Pendiente</th>
                          <th className="py-3 pr-4">Estado</th>
                          <th className="py-3 pr-4">Accion</th>
                        </tr>
                      </thead>
                      <tbody>
                        {order.items.map((item) => (
                          <tr className="border-b last:border-0" key={item.id}>
                            <td className="py-3 pr-4 font-semibold">{item.item_name_snapshot}</td>
                            <td className="py-3 pr-4">{itemTypeLabel(item.item_type_snapshot)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_delivered)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_consumed)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_returned)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_returned_damaged)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_lost)}</td>
                            <td className="py-3 pr-4">{quantity(item.quantity_discarded)}</td>
                            <td className="py-3 pr-4">{quantity(outcomePending(item))}</td>
                            <td className="py-3 pr-4">
                              <Badge tone={item.outcome_status === "RECORDED" ? "success" : item.outcome_status === "PENDING" ? "neutral" : "warning"}>
                                {outcomeLabel(item.outcome_status)}
                              </Badge>
                            </td>
                            <td className="py-3 pr-4">
                              {canOperate && ["DELIVERED", "PARTIALLY_DELIVERED", "OUTCOME_PENDING", "WITH_DIFFERENCES"].includes(order.status) ? (
                                <Button size="sm" type="button" variant="secondary" onClick={() => setOutcomeTarget(item)}>
                                  Registrar resultado
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
            {["OUTCOME_RECORDED", "WITH_DIFFERENCES", "CLOSED"].includes(order.status) ? (
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
                      <ClosureMetric label="Cerrado por" value={order.closed_by || "-"} />
                      <ClosureMetric label="Fecha de cierre" value={order.closed_at ? new Date(order.closed_at).toLocaleString("es-CL") : "-"} />
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
            {purchaseOpen ? (
              <PurchaseRequestModal
                order={order}
                stockCheck={stockCheck}
                warehouses={warehouses}
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
          </>
        ) : null}
      </div>
    </RoleGuard>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-bold">{value}</p>
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

function StatusBadge({ status }: { status: LogisticsOrderStatus }) {
  const tone =
    status === "CANCELLED"
      ? "danger"
      : status === "INSUFFICIENT_STOCK" || status === "WITH_DIFFERENCES"
        ? "warning"
        : "success";
  return <Badge tone={tone}>{statusLabels[status]}</Badge>;
}

function PurchaseRequestModal({
  order,
  stockCheck,
  warehouses,
  saving,
  onClose,
  onSubmit
}: {
  order: LogisticsOrder;
  stockCheck: LogisticsOrderStockCheck | null;
  warehouses: Warehouse[];
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
  const [mode, setMode] = useState<PurchaseDeliveryMode>("TO_WAREHOUSE");
  const [warehouseId, setWarehouseId] = useState(order.warehouse_id || warehouses[0]?.id || "");
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
  const valid = title.trim().length > 0 && missingItems.length > 0 && (mode === "DIRECT_TO_EVENT" || Boolean(warehouseId));

  return (
    <ModalShell title="Crear solicitud de compra" description={order.title} size="lg" onClose={onClose}>
      <form
        className="space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          if (!valid) return;
          void onSubmit({
            title: title.trim(),
            delivery_mode: mode,
            warehouse_id: mode === "TO_WAREHOUSE" ? warehouseId : null,
            notes: notes || null
          });
        }}
      >
        <label className="grid gap-2 text-sm font-semibold">
          Titulo
          <Input value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Modo de entrega
            <select
              className="h-11 rounded-md border px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              value={mode}
              onChange={(event) => setMode(event.target.value as PurchaseDeliveryMode)}
            >
              <option value="TO_WAREHOUSE">Recibir en bodega</option>
              <option value="DIRECT_TO_EVENT">Entregar directo al evento</option>
            </select>
          </label>
          {mode === "TO_WAREHOUSE" ? (
            <label className="grid gap-2 text-sm font-semibold">
              Bodega destino
              <select
                className="h-11 rounded-md border px-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                value={warehouseId}
                onChange={(event) => setWarehouseId(event.target.value)}
              >
                <option value="">Selecciona bodega</option>
                {warehouses.map((warehouse) => (
                  <option key={warehouse.id} value={warehouse.id}>
                    {warehouse.name}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
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
        {mode === "DIRECT_TO_EVENT" ? (
          <p className="text-sm font-semibold text-amber-700">La entrega directa al evento no aumenta stock de bodega.</p>
        ) : null}
        {!valid ? (
          <p className="text-sm font-semibold text-amber-700">Debes tener faltantes, titulo y bodega destino cuando la compra entra a bodega.</p>
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
  item,
  saving,
  onClose,
  onSubmit
}: {
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
        <div className="rounded-lg border bg-slate-50 p-3 text-sm">
          <p>Entregado: <span className="font-semibold">{quantity(item.quantity_delivered)}</span> {item.unit_snapshot || ""}</p>
          <p className="mt-1">Pendiente por explicar: <span className="font-semibold">{quantity(pending)}</span></p>
        </div>
        {item.item_type_snapshot === "CONSUMABLE" ? (
          <div className="space-y-2 rounded-lg border p-3 text-sm">
            <p className="text-muted-foreground">
              Este producto no requiere retorno. Si sobro y volvio fisicamente a bodega, registra cantidad devuelta.
            </p>
            <Button type="button" variant="secondary" onClick={markAllConsumed}>
              Marcar todo como consumido/asignado al evento
            </Button>
          </div>
        ) : null}
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
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Guardar resultado"}</Button>
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
