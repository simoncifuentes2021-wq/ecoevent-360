"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Eye, Plus, Search, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { getEvents } from "@/lib/api/events";
import { getInventoryItems } from "@/lib/api/inventory";
import { createEventLogisticsOrder, getLogisticsOrders } from "@/lib/api/logistics-orders";
import { getUsers } from "@/lib/api/users";
import { getWarehouses } from "@/lib/api/warehouses";
import type { Event } from "@/types/event";
import type { InventoryItem } from "@/types/inventory";
import type { LogisticsOrder, LogisticsOrderCreate, LogisticsOrderStatus } from "@/types/logistics-order";
import type { User } from "@/types/user";
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

const statuses: LogisticsOrderStatus[] = [
  "ASSIGNED",
  "RESERVED",
  "IN_PREPARATION",
  "LOADED",
  "OUT_OF_WAREHOUSE",
  "DELIVERED",
  "PARTIALLY_DELIVERED",
  "OUTCOME_PENDING",
  "OUTCOME_RECORDED",
  "WITH_DIFFERENCES",
  "CLOSED",
  "CANCELLED"
];

export default function SupervisorLogisticsOrdersPage() {
  const [orders, setOrders] = useState<LogisticsOrder[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [products, setProducts] = useState<InventoryItem[]>([]);
  const [operators, setOperators] = useState<User[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orderResponse, eventResponse, warehouseResponse, productResponse, operatorResponse] = await Promise.all([
        getLogisticsOrders({ page: 1, limit: 100 }),
        getEvents({ page: 1, limit: 100 }),
        getWarehouses({ is_active: true, limit: 100 }),
        getInventoryItems({ is_active: true, limit: 100 }),
        getUsers({ role: "LOGISTICS_OPERATOR", is_active: true, limit: 100 })
      ]);
      setOrders(orderResponse.items);
      setEvents(eventResponse.items);
      setWarehouses(warehouseResponse.items);
      setProducts(productResponse.items);
      setOperators(operatorResponse.items.filter((user) => user.role === "LOGISTICS_OPERATOR" && user.is_active));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los pedidos logisticos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    return orders.filter((order) => {
      const text = [
        order.title,
        order.event?.name,
        order.warehouse?.name,
        order.assigned_operator?.full_name,
        order.status
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return (!query || text.includes(query)) && (!status || order.status === status);
    });
  }, [orders, q, status]);

  const columns: DataTableColumn<LogisticsOrder>[] = [
    { key: "title", header: "Pedido", cell: (order) => <span className="font-semibold">{order.title}</span> },
    { key: "event", header: "Evento", cell: (order) => order.event?.name || "-" },
    { key: "warehouse", header: "Bodega", cell: (order) => order.warehouse?.name || "-" },
    { key: "operator", header: "Operador", cell: (order) => order.assigned_operator?.full_name || "-" },
    { key: "items", header: "Productos", cell: (order) => order.items.length },
    { key: "total", header: "Total estimado", cell: (order) => money(order.total_estimated_amount) },
    { key: "status", header: "Estado", cell: (order) => <StatusBadge status={order.status} /> }
  ];

  async function submitQuickOrder(eventId: string, data: LogisticsOrderCreate) {
    await createEventLogisticsOrder(eventId, data);
    setFormOpen(false);
    await load();
  }

  return (
    <RoleGuard roles={["SUPERVISOR"]}>
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <PageHeader
            eyebrow="Supervision"
            title="Pedidos logisticos"
            description="Pedidos logisticos vinculados a tus eventos asignados."
          />
          <Button onClick={() => setFormOpen(true)} type="button">
            <Plus className="h-4 w-4" />
            Crear pedido rapido
          </Button>
        </div>

        <Card>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-[1fr_260px]">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                <Input
                  className="pl-9"
                  placeholder="Buscar pedido, evento, bodega u operador"
                  value={q}
                  onChange={(event) => setQ(event.target.value)}
                />
              </div>
              <select className="h-10 rounded-md border bg-white px-3 text-sm" value={status} onChange={(event) => setStatus(event.target.value)}>
                <option value="">Todos los estados</option>
                {statuses.map((item) => (
                  <option key={item} value={item}>
                    {statusLabels[item]}
                  </option>
                ))}
              </select>
            </div>
          </CardContent>
        </Card>

        {!loading && !error && filtered.length === 0 ? (
          <EmptyState title="Sin pedidos logisticos" description="Cuando crees pedidos desde la pestana Logistica de tus eventos, apareceran aqui." />
        ) : (
          <DataTable
            actions={(order) => (
              <Link href={`/supervisor/logistica/pedidos/${order.id}`}>
                <Button size="sm" type="button" variant="secondary">
                  <Eye className="h-4 w-4" />
                  Ver
                </Button>
              </Link>
            )}
            columns={columns}
            data={filtered}
            emptyTitle="Sin pedidos logisticos"
            error={error}
            getRowKey={(order) => order.id}
            loading={loading}
          />
        )}
        {formOpen ? (
          <QuickOrderModal
            events={events}
            operators={operators}
            products={products}
            warehouses={warehouses}
            onClose={() => setFormOpen(false)}
            onSubmit={submitQuickOrder}
          />
        ) : null}
      </div>
    </RoleGuard>
  );
}

type ItemRow = {
  item_id: string;
  quantity_requested: string;
  notes: string;
};

type QuickOrderState = {
  event_id: string;
  title: string;
  warehouse_id: string;
  assigned_operator_id: string;
  delivery_zone: string;
  delivery_notes: string;
  items: ItemRow[];
};

function QuickOrderModal({
  events,
  warehouses,
  products,
  operators,
  onClose,
  onSubmit
}: {
  events: Event[];
  warehouses: Warehouse[];
  products: InventoryItem[];
  operators: User[];
  onClose: () => void;
  onSubmit: (eventId: string, data: LogisticsOrderCreate) => Promise<void>;
}) {
  const [form, setForm] = useState<QuickOrderState>({
    event_id: events[0]?.id || "",
    title: "",
    warehouse_id: warehouses[0]?.id || "",
    assigned_operator_id: operators[0]?.id || "",
    delivery_zone: "",
    delivery_notes: "",
    items: []
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [productQuery, setProductQuery] = useState("");
  const selectedProductIds = useMemo(() => new Set(form.items.map((item) => item.item_id)), [form.items]);
  const filteredProducts = useMemo(() => {
    const query = productQuery.trim().toLowerCase();
    return products
      .filter((product) => !selectedProductIds.has(product.id))
      .filter((product) => {
        if (!query) return true;
        return [product.name, product.sku, product.unit, product.item_type]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query));
      })
      .slice(0, 8);
  }, [productQuery, products, selectedProductIds]);
  const total = useMemo(
    () =>
      form.items.reduce((sum, row) => {
        const product = products.find((item) => item.id === row.item_id);
        return sum + Number(product?.unit_price || 0) * Number(row.quantity_requested || 0);
      }, 0),
    [form.items, products]
  );
  const valid =
    form.event_id &&
    form.title.trim() &&
    form.warehouse_id &&
    form.assigned_operator_id &&
    form.items.length > 0 &&
    form.items.every((row) => Number(row.quantity_requested) > 0);

  function addProduct(product: InventoryItem) {
    setForm((current) => ({
      ...current,
      items: [...current.items, { item_id: product.id, quantity_requested: "1", notes: "" }]
    }));
    setProductQuery("");
  }

  function updateRow(index: number, data: Partial<ItemRow>) {
    setForm((current) => ({
      ...current,
      items: current.items.map((row, rowIndex) => (rowIndex === index ? { ...row, ...data } : row))
    }));
  }

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form.event_id, {
        title: form.title.trim(),
        warehouse_id: form.warehouse_id,
        assigned_operator_id: form.assigned_operator_id,
        description: null,
        delivery_zone: form.delivery_zone || null,
        delivery_notes: form.delivery_notes || null,
        items: form.items.map((row) => ({
          item_id: row.item_id,
          quantity_requested: Number(row.quantity_requested),
          notes: row.notes || null
        }))
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo crear el pedido logistico.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      description="Crea un pedido para uno de tus eventos asignados."
      onClose={onClose}
      size="lg"
      title="Crear pedido logistico rapido"
    >
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Evento
            <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.event_id} onChange={(event) => setForm({ ...form, event_id: event.target.value })}>
              <option value="">Seleccionar evento</option>
              {events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Titulo del pedido
            <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Bodega
            <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.warehouse_id} onChange={(event) => setForm({ ...form, warehouse_id: event.target.value })}>
              <option value="">Seleccionar bodega</option>
              {warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Operador logistico
            <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.assigned_operator_id} onChange={(event) => setForm({ ...form, assigned_operator_id: event.target.value })}>
              <option value="">Seleccionar operador</option>
              {operators.map((operator) => <option key={operator.id} value={operator.id}>{operator.full_name}</option>)}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Zona/lugar entrega
            <Input value={form.delivery_zone} onChange={(event) => setForm({ ...form, delivery_zone: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Observaciones
            <Input value={form.delivery_notes} onChange={(event) => setForm({ ...form, delivery_notes: event.target.value })} />
          </label>
        </div>

        <Card>
          <CardContent className="space-y-3">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                className="pl-9"
                placeholder="Buscar producto por nombre, SKU o tipo"
                value={productQuery}
                onChange={(event) => setProductQuery(event.target.value)}
              />
            </div>
            <div className="grid max-h-64 gap-2 overflow-y-auto pr-1">
              {filteredProducts.length === 0 ? (
                <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">No hay productos disponibles con esa busqueda.</div>
              ) : (
                filteredProducts.map((product) => (
                  <button
                    className="grid gap-2 rounded-md border bg-white p-3 text-left transition hover:border-primary hover:bg-emerald-50 md:grid-cols-[1fr_100px_110px]"
                    key={product.id}
                    onClick={() => addProduct(product)}
                    type="button"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-semibold">{product.name}</p>
                      <p className="text-xs text-muted-foreground">{product.sku || "Sin SKU"}</p>
                    </div>
                    <span className="text-sm">{product.unit || "-"}</span>
                    <span className="text-sm font-semibold">{money(product.unit_price || 0)}</span>
                  </button>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        <div className="space-y-3">
          {form.items.map((row, index) => {
            const product = products.find((item) => item.id === row.item_id);
            return (
              <div className="grid gap-3 rounded-lg border p-3 md:grid-cols-[1fr_120px_1fr_44px] md:items-center" key={row.item_id}>
                <div className="min-w-0">
                  <p className="truncate font-semibold">{product?.name || "Producto"}</p>
                  <p className="text-xs text-muted-foreground">{product?.unit || "Sin unidad"} - {money(product?.unit_price || 0)}</p>
                </div>
                <label className="grid gap-1 text-sm font-semibold">
                  Cantidad
                  <Input min={1} step="1" type="number" value={row.quantity_requested} onChange={(event) => updateRow(index, { quantity_requested: event.target.value })} />
                </label>
                <label className="grid gap-1 text-sm font-semibold">
                  Nota
                  <Input value={row.notes} onChange={(event) => updateRow(index, { notes: event.target.value })} />
                </label>
                <Button aria-label="Quitar producto" type="button" variant="ghost" onClick={() => setForm({ ...form, items: form.items.filter((_, rowIndex) => rowIndex !== index) })}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            );
          })}
          {form.items.length === 0 ? (
            <div className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">Busca productos y agrégalos al pedido.</div>
          ) : null}
        </div>

        <div className="rounded-lg border bg-slate-50 p-4 text-right">
          <p className="text-sm text-muted-foreground">Total estimado</p>
          <p className="text-2xl font-bold">{money(total)}</p>
        </div>
        {!valid ? <p className="text-sm font-semibold text-amber-700">Selecciona evento, bodega, operador y al menos un producto con cantidad mayor a 0.</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Crear pedido"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function StatusBadge({ status }: { status: LogisticsOrderStatus }) {
  const tone =
    status === "CANCELLED"
      ? "danger"
      : status === "INSUFFICIENT_STOCK" || status === "WITH_DIFFERENCES"
        ? "warning"
        : status === "CLOSED"
          ? "neutral"
          : "success";
  return <Badge tone={tone}>{statusLabels[status]}</Badge>;
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}
