"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Eye, PackageCheck, Search, ShoppingCart, Truck, X } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { LogisticsEvidenceUploader } from "@/components/logistics/LogisticsEvidenceUploader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/hooks/useAuth";
import {
  approvePurchaseRequest,
  cancelPurchaseRequest,
  deliverPurchaseRequestDirectToEvent,
  getPurchaseRequests,
  markPurchaseRequestPurchased,
  receivePurchaseRequest,
  rejectPurchaseRequest
} from "@/lib/api/purchase-requests";
import { getMyWarehouseAssignments } from "@/lib/api/warehouses";
import type { PurchaseDeliveryMode, PurchaseRequest, PurchaseRequestStatus } from "@/types/purchase-request";
import type { MyWarehouseAssignment } from "@/types/warehouse";

const statusLabels: Record<PurchaseRequestStatus, string> = {
  REQUESTED: "Solicitada",
  APPROVED: "Aprobada",
  REJECTED: "Rechazada",
  PURCHASED: "Comprada",
  PARTIALLY_RECEIVED: "Recepcion parcial",
  RECEIVED: "Recibida",
  DELIVERED_DIRECT_TO_EVENT: "Directo al evento",
  CANCELLED: "Cancelada"
};

const modeLabels: Record<PurchaseDeliveryMode, string> = {
  TO_WAREHOUSE: "A bodega",
  DIRECT_TO_EVENT: "Directo al evento"
};

export default function AdminPurchasesPage() {
  const { user } = useAuth();
  const [purchases, setPurchases] = useState<PurchaseRequest[]>([]);
  const [assignments, setAssignments] = useState<MyWarehouseAssignment[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detail, setDetail] = useState<PurchaseRequest | null>(null);
  const [action, setAction] = useState<{ type: "reject" | "purchase" | "receive" | "direct"; purchase: PurchaseRequest } | null>(null);
  const [saving, setSaving] = useState(false);
  const isAdmin = user?.role === "SUPER_ADMIN" || user?.role === "ADMIN";
  const isLogisticsOperator = user?.role === "LOGISTICS_OPERATOR";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getPurchaseRequests({ page: 1, limit: 100 });
      setPurchases(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar las compras.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!isLogisticsOperator) return;
    void getMyWarehouseAssignments()
      .then(setAssignments)
      .catch(() => setAssignments([]));
  }, [isLogisticsOperator]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    if (!query) return purchases;
    return purchases.filter((purchase) =>
      [purchase.title, purchase.event?.name, purchase.logistics_order?.title, purchase.warehouse?.name, purchase.status]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [purchases, q]);

  const metrics = useMemo(
    () => ({
      requested: purchases.filter((item) => item.status === "REQUESTED").length,
      approved: purchases.filter((item) => item.status === "APPROVED").length,
      purchased: purchases.filter((item) => item.status === "PURCHASED").length,
      received: purchases.filter((item) => item.status === "RECEIVED" || item.status === "DELIVERED_DIRECT_TO_EVENT").length,
      estimated: purchases.reduce((sum, item) => sum + Number(item.total_estimated_amount || 0), 0)
    }),
    [purchases]
  );

  const columns: DataTableColumn<PurchaseRequest>[] = [
    { key: "requested_at", header: "Fecha", cell: (row) => new Date(row.requested_at).toLocaleDateString("es-CL") },
    { key: "title", header: "Titulo", cell: (row) => <span className="font-semibold">{row.title}</span> },
    { key: "event", header: "Evento", cell: (row) => row.event?.name || "-" },
    { key: "order", header: "Pedido", cell: (row) => row.logistics_order?.title || "-" },
    { key: "mode", header: "Modo", cell: (row) => modeLabels[row.delivery_mode] },
    { key: "status", header: "Estado", cell: (row) => <PurchaseStatusBadge status={row.status} /> },
    { key: "estimated", header: "Estimado", cell: (row) => money(row.total_estimated_amount) },
    { key: "purchased", header: "Comprado", cell: (row) => money(row.total_purchased_amount) },
    { key: "requester", header: "Solicitado por", cell: (row) => row.requester?.full_name || row.requester?.email || "-" }
  ];

  async function runAction(task: () => Promise<PurchaseRequest>) {
    setSaving(true);
    setError(null);
    try {
      await task();
      setAction(null);
      setDetail(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo completar la accion.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN", "LOGISTICS_OPERATOR"]}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Stock"
          title="Compras"
          description="Solicitudes por falta de stock asociadas a pedidos logisticos, eventos y bodegas."
        />

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <Metric label="Solicitudes pendientes" value={metrics.requested} />
          <Metric label="Aprobadas" value={metrics.approved} />
          <Metric label="Compradas" value={metrics.purchased} />
          <Metric label="Recibidas" value={metrics.received} />
          <Metric label="Monto estimado" value={money(metrics.estimated)} />
        </section>

        <Card>
          <CardContent>
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input className="pl-9" placeholder="Buscar compra, evento, pedido o bodega" value={q} onChange={(event) => setQ(event.target.value)} />
            </div>
          </CardContent>
        </Card>

        {error ? <ErrorState message={error} onRetry={load} /> : null}
        <DataTable
          actions={(purchase) => (
            <div className="flex justify-end gap-2">
              <Button size="sm" type="button" variant="secondary" onClick={() => setDetail(purchase)}>
                <Eye className="h-4 w-4" />
              </Button>
              {isAdmin && purchase.status === "REQUESTED" ? (
                <>
                  <Button size="sm" type="button" onClick={() => void runAction(() => approvePurchaseRequest(purchase.id))}>
                    <Check className="h-4 w-4" />
                  </Button>
                  <Button size="sm" type="button" variant="ghost" onClick={() => setAction({ type: "reject", purchase })}>
                    <X className="h-4 w-4" />
                  </Button>
                </>
              ) : null}
              {canMarkPurchased(purchase, isAdmin, assignments) ? (
                <Button size="sm" type="button" variant="secondary" onClick={() => setAction({ type: "purchase", purchase })}>
                  <ShoppingCart className="h-4 w-4" />
                </Button>
              ) : null}
              {canReceivePurchase(purchase, isAdmin, assignments) ? (
                <Button
                  size="sm"
                  type="button"
                  variant="secondary"
                  onClick={() => setAction({ type: purchase.delivery_mode === "DIRECT_TO_EVENT" ? "direct" : "receive", purchase })}
                >
                  {purchase.delivery_mode === "DIRECT_TO_EVENT" ? <Truck className="h-4 w-4" /> : <PackageCheck className="h-4 w-4" />}
                </Button>
              ) : null}
              {canCancelPurchase(purchase, user?.id, isAdmin) ? (
                <Button size="sm" type="button" variant="ghost" onClick={() => void runAction(() => cancelPurchaseRequest(purchase.id))}>
                  Cancelar
                </Button>
              ) : null}
            </div>
          )}
          columns={columns}
          data={filtered}
          emptyTitle="Sin compras"
          emptyDescription="Las solicitudes por faltante de stock apareceran aqui."
          getRowKey={(row) => row.id}
          loading={loading}
        />

        {detail ? <PurchaseDetailModal purchase={detail} onClose={() => setDetail(null)} /> : null}
        {action ? (
          <PurchaseActionModal
            action={action}
            saving={saving}
            onClose={() => setAction(null)}
            onReject={(rejection_reason) => runAction(() => rejectPurchaseRequest(action.purchase.id, { rejection_reason }))}
            onMarkPurchased={(payload) => runAction(() => markPurchaseRequestPurchased(action.purchase.id, payload))}
            onReceive={(payload) =>
              runAction(() =>
                action.type === "direct"
                  ? deliverPurchaseRequestDirectToEvent(action.purchase.id, payload)
                  : receivePurchaseRequest(action.purchase.id, payload)
              )
            }
          />
        ) : null}
      </div>
    </RoleGuard>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}

function PurchaseDetailModal({ purchase, onClose }: { purchase: PurchaseRequest; onClose: () => void }) {
  return (
    <ModalShell title={purchase.title} description={`${modeLabels[purchase.delivery_mode]} - ${statusLabels[purchase.status]}`} size="lg" onClose={onClose}>
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-3">
          <Info label="Evento" value={purchase.event?.name || "-"} />
          <Info label="Pedido" value={purchase.logistics_order?.title || "-"} />
          <Info label="Bodega" value={purchase.warehouse?.name || "-"} />
          <Info label="Solicitado por" value={purchase.requester?.full_name || "-"} />
          <Info label="Total estimado" value={money(purchase.total_estimated_amount)} />
          <Info label="Total comprado" value={money(purchase.total_purchased_amount)} />
        </div>
        {purchase.notes ? <p className="rounded-md border bg-slate-50 p-3 text-sm">{purchase.notes}</p> : null}
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="border-b text-xs uppercase text-muted-foreground">
              <tr>
                <th className="py-3 pr-4">Producto</th>
                <th className="py-3 pr-4">Solicitado</th>
                <th className="py-3 pr-4">Comprado</th>
                <th className="py-3 pr-4">Recibido</th>
                <th className="py-3 pr-4">Precio estimado</th>
                <th className="py-3 pr-4">Precio comprado</th>
                <th className="py-3 pr-4">Total</th>
              </tr>
            </thead>
            <tbody>
              {purchase.items.map((item) => (
                <tr className="border-b last:border-0" key={item.id}>
                  <td className="py-3 pr-4 font-semibold">{item.item_name_snapshot}</td>
                  <td className="py-3 pr-4">{quantity(item.quantity_requested)} {item.unit_snapshot || ""}</td>
                  <td className="py-3 pr-4">{quantity(item.quantity_purchased)}</td>
                  <td className="py-3 pr-4">{quantity(item.quantity_received)}</td>
                  <td className="py-3 pr-4">{money(item.unit_price_estimated)}</td>
                  <td className="py-3 pr-4">{money(item.unit_price_purchased)}</td>
                  <td className="py-3 pr-4">{money(Number(item.total_purchased) || Number(item.total_estimated))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <LogisticsEvidenceUploader
            purchaseRequestId={purchase.id}
            stage="PURCHASE_REQUEST"
            title="Evidencias de solicitud"
          />
          <LogisticsEvidenceUploader
            purchaseRequestId={purchase.id}
            stage="PURCHASE_RECEIPT"
            title="Boleta, factura o cotizacion"
          />
          <LogisticsEvidenceUploader
            purchaseRequestId={purchase.id}
            stage="PURCHASE_WAREHOUSE_RECEIPT"
            title="Evidencia de recepcion en bodega"
          />
          <LogisticsEvidenceUploader
            purchaseRequestId={purchase.id}
            stage="PURCHASE_DIRECT_EVENT_DELIVERY"
            title="Evidencia de entrega directa al evento"
          />
        </div>
      </div>
    </ModalShell>
  );
}

function PurchaseActionModal({
  action,
  saving,
  onClose,
  onReject,
  onMarkPurchased,
  onReceive
}: {
  action: { type: "reject" | "purchase" | "receive" | "direct"; purchase: PurchaseRequest };
  saving: boolean;
  onClose: () => void;
  onReject: (reason: string) => void;
  onMarkPurchased: (payload: Parameters<typeof markPurchaseRequestPurchased>[1]) => void;
  onReceive: (payload: Parameters<typeof receivePurchaseRequest>[1]) => void;
}) {
  const [notes, setNotes] = useState("");
  const [rows, setRows] = useState(() =>
    action.purchase.items.map((item) => ({
      id: item.id,
      quantity: String(action.type === "purchase" ? Number(item.quantity_requested || 0) : remainingToReceive(item)),
      price: String(Number(item.unit_price_purchased || item.unit_price_estimated || 0))
    }))
  );

  function updateRow(id: string, data: Partial<(typeof rows)[number]>) {
    setRows((current) => current.map((row) => (row.id === id ? { ...row, ...data } : row)));
  }

  function submit() {
    if (action.type === "reject") {
      onReject(notes);
      return;
    }
    if (action.type === "purchase") {
      onMarkPurchased({
        notes,
        items: rows.map((row) => ({
          purchase_request_item_id: row.id,
          quantity_purchased: Number(row.quantity || 0),
          unit_price_purchased: Number(row.price || 0)
        }))
      });
      return;
    }
    onReceive({
      notes,
      items: rows.map((row) => ({
        purchase_request_item_id: row.id,
        quantity_received: Number(row.quantity || 0)
      }))
    });
  }

  return (
    <ModalShell
      title={actionTitle(action.type)}
      description={action.purchase.title}
      size={action.type === "reject" ? "md" : "lg"}
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); submit(); }}>
        {action.type !== "reject" ? (
          <div className="space-y-3">
            {action.purchase.items.map((item) => {
              const row = rows.find((value) => value.id === item.id)!;
              const rowQuantity = Number(row.quantity || 0);
              const rowPrice = Number(row.price || 0);
              const maxQuantity = action.type === "purchase" ? Number(item.quantity_requested || 0) : remainingToReceive(item);
              const validRow =
                Number.isInteger(rowQuantity) &&
                rowQuantity > 0 &&
                rowQuantity <= maxQuantity &&
                (action.type !== "purchase" || (Number.isInteger(rowPrice) && rowPrice >= 0));
              return (
                <div className="grid gap-3 rounded-lg border p-3 md:grid-cols-[1fr_140px_140px] md:items-center" key={item.id}>
                  <div>
                    <p className="font-semibold">{item.item_name_snapshot}</p>
                    <p className="text-xs text-muted-foreground">Solicitado {quantity(item.quantity_requested)} · Recibido {quantity(item.quantity_received)}</p>
                  </div>
                  <label className="grid gap-1 text-sm font-semibold">
                    {action.type === "purchase" ? "Cantidad comprada" : "Cantidad recibida"}
                    <Input min={1} step="1" type="number" value={row.quantity} onChange={(event) => updateRow(item.id, { quantity: event.target.value })} />
                  </label>
                  {action.type === "purchase" ? (
                    <label className="grid gap-1 text-sm font-semibold">
                      Precio unitario
                      <Input min={0} step="1" type="number" value={row.price} onChange={(event) => updateRow(item.id, { price: event.target.value })} />
                    </label>
                  ) : null}
                  {!validRow ? (
                    <p className="text-xs font-semibold text-amber-700 md:col-span-3">
                      Usa numeros enteros. La cantidad debe ser mayor a 0 y no superar lo pendiente.
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : null}
        <label className="grid gap-2 text-sm font-semibold">
          {action.type === "reject" ? "Motivo de rechazo" : "Notas"}
          <textarea className="min-h-24 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={notes} onChange={(event) => setNotes(event.target.value)} />
        </label>
        {action.type === "direct" ? <p className="text-sm font-semibold text-amber-700">La entrega directa al evento no aumenta stock de bodega.</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={saving || (action.type === "reject" && !notes.trim()) || !isPurchaseActionValid(action.type, rows, action.purchase)} type="submit">{saving ? "Guardando..." : "Confirmar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function isPurchaseActionValid(
  type: "reject" | "purchase" | "receive" | "direct",
  rows: Array<{ id: string; quantity: string; price: string }>,
  purchase: PurchaseRequest
) {
  if (type === "reject") return true;
  return rows.every((row) => {
    const item = purchase.items.find((value) => value.id === row.id);
    if (!item) return false;
    const rowQuantity = Number(row.quantity || 0);
    const maxQuantity = type === "purchase" ? Number(item.quantity_requested || 0) : remainingToReceive(item);
    if (!Number.isInteger(rowQuantity) || rowQuantity <= 0 || rowQuantity > maxQuantity) return false;
    if (type !== "purchase") return true;
    const rowPrice = Number(row.price || 0);
    return Number.isInteger(rowPrice) && rowPrice >= 0;
  });
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}

function PurchaseStatusBadge({ status }: { status: PurchaseRequestStatus }) {
  const tone = status === "REJECTED" || status === "CANCELLED" ? "danger" : status === "REQUESTED" ? "warning" : "success";
  return <Badge tone={tone}>{statusLabels[status]}</Badge>;
}

function actionTitle(type: "reject" | "purchase" | "receive" | "direct") {
  if (type === "reject") return "Rechazar compra";
  if (type === "purchase") return "Marcar como comprada";
  if (type === "direct") return "Registrar entrega directa al evento";
  return "Recibir compra en bodega";
}

function remainingToReceive(item: PurchaseRequest["items"][number]) {
  const purchased = Number(item.quantity_purchased || 0);
  const requested = Number(item.quantity_requested || 0);
  const received = Number(item.quantity_received || 0);
  return Math.max((purchased || requested) - received, 0);
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}

function quantity(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 0 });
}

function canMarkPurchased(purchase: PurchaseRequest, isAdmin: boolean, assignments: MyWarehouseAssignment[]) {
  if (purchase.status !== "APPROVED") return false;
  if (isAdmin) return true;
  if (!purchase.warehouse_id) return false;
  return assignments.some((assignment) => assignment.warehouse_id === purchase.warehouse_id && assignment.can_manage_stock);
}

function canReceivePurchase(purchase: PurchaseRequest, isAdmin: boolean, assignments: MyWarehouseAssignment[]) {
  if (!["APPROVED", "PURCHASED", "PARTIALLY_RECEIVED"].includes(purchase.status)) return false;
  if (purchase.delivery_mode === "DIRECT_TO_EVENT") return isAdmin || purchase.logistics_order_id !== null;
  if (isAdmin) return true;
  if (!purchase.warehouse_id) return false;
  return assignments.some((assignment) => assignment.warehouse_id === purchase.warehouse_id && assignment.can_manage_stock);
}

function canCancelPurchase(purchase: PurchaseRequest, userId: string | undefined, isAdmin: boolean) {
  if (!["REQUESTED", "APPROVED", "PURCHASED", "PARTIALLY_RECEIVED"].includes(purchase.status)) return false;
  if (isAdmin) return true;
  return purchase.status === "REQUESTED" && Boolean(userId) && purchase.requested_by === userId;
}
