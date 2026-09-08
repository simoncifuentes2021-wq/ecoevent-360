"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardList, Plus, Search, SlidersHorizontal, Trash2, X } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { LogisticsOrdersOverview, logisticsStatusLabels } from "@/components/logistics/LogisticsOrdersOverview";
import { WarehouseProductCatalog } from "@/components/logistics/WarehouseProductCatalog";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { getEvents } from "@/lib/api/events";
import { getAllInventoryItems } from "@/lib/api/inventory";
import { createEventLogisticsOrder, getLogisticsOrders } from "@/lib/api/logistics-orders";
import { getAllStockBalances } from "@/lib/api/stock";
import { getUsers } from "@/lib/api/users";
import { getWarehouses } from "@/lib/api/warehouses";
import type { Event } from "@/types/event";
import type { InventoryItem } from "@/types/inventory";
import type { LogisticsOrder, LogisticsOrderCreate, LogisticsOrderStatus } from "@/types/logistics-order";
import type { StockBalance } from "@/types/stock";
import type { User } from "@/types/user";
import type { Warehouse } from "@/types/warehouse";

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
  const [stock, setStock] = useState<StockBalance[]>([]);
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
      const [orderResponse, eventResponse, warehouseResponse, allProducts, allStock, operatorResponse] = await Promise.all([
        getLogisticsOrders({ page: 1, limit: 100 }),
        getEvents({ page: 1, limit: 100 }),
        getWarehouses({ is_active: true, limit: 100 }),
        getAllInventoryItems({ is_active: true }),
        getAllStockBalances(),
        getUsers({ role: "LOGISTICS_OPERATOR", is_active: true, limit: 100 })
      ]);
      setOrders(orderResponse.items);
      setEvents(eventResponse.items);
      setWarehouses(warehouseResponse.items);
      setProducts(allProducts);
      setStock(allStock);
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

        <section className="grid gap-3 sm:grid-cols-3">
          <Summary icon={ClipboardList} label="Pedidos visibles" value={orders.length} />
          <Summary icon={AlertTriangle} label="Requieren atención" value={orders.filter((order) => ["INSUFFICIENT_STOCK", "WITH_DIFFERENCES", "OBSERVED"].includes(order.status)).length} warning />
          <Summary icon={CheckCircle2} label="Completados" value={orders.filter((order) => order.status === "CLOSED").length} />
        </section>

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
                <SlidersHorizontal className="h-4 w-4 text-emerald-700" /> Buscar y filtrar
              </div>
              <span className="text-xs font-semibold text-slate-500">{filtered.length} resultados</span>
            </div>
            <div className="grid gap-3 md:grid-cols-[1fr_260px_auto]">
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
                    {logisticsStatusLabels[item]}
                  </option>
                ))}
              </select>
              <Button disabled={!q && !status} type="button" variant="ghost" onClick={() => { setQ(""); setStatus(""); }}>
                <X className="h-4 w-4" /> Limpiar
              </Button>
            </div>
          </CardContent>
        </Card>

        <LogisticsOrdersOverview
          orders={filtered}
          loading={loading}
          error={error}
          onRetry={load}
          hrefFor={(order) => `/supervisor/logistica/pedidos/${order.id}`}
          emptyTitle="Sin pedidos logísticos"
          emptyDescription="Cuando crees pedidos desde la pestaña Logística de tus eventos, aparecerán aquí."
        />
        {formOpen ? (
          <QuickOrderModal
            events={events}
            operators={operators}
            products={products}
            stock={stock}
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
  stock,
  operators,
  onClose,
  onSubmit
}: {
  events: Event[];
  warehouses: Warehouse[];
  products: InventoryItem[];
  stock: StockBalance[];
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
    form.items.every((row) => isPositiveInteger(row.quantity_requested));

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

        <WarehouseProductCatalog
          onAdd={addProduct}
          onQueryChange={setProductQuery}
          products={products}
          query={productQuery}
          selectedProductIds={selectedProductIds}
          stock={stock}
          warehouseId={form.warehouse_id}
          warehouses={warehouses}
        />

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
        {!valid ? <p className="text-sm font-semibold text-amber-700">Selecciona evento, bodega, operador y al menos un producto con cantidad entera mayor a 0.</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Crear pedido"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function Summary({ icon: Icon, label, value, warning = false }: { icon: typeof ClipboardList; label: string; value: number; warning?: boolean }) {
  return (
    <Card className={warning ? "border-amber-200 bg-amber-50/40" : "border-slate-200"}>
      <CardContent className="flex items-center gap-3 p-4">
        <span className={`grid h-10 w-10 place-items-center rounded-xl ${warning ? "bg-amber-100 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>
          <Icon className="h-5 w-5" />
        </span>
        <div><p className="text-xs font-semibold text-slate-500">{label}</p><p className="text-2xl font-extrabold text-slate-950">{value}</p></div>
      </CardContent>
    </Card>
  );
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}

function isPositiveInteger(value: string | number) {
  const numberValue = Number(value);
  return Number.isInteger(numberValue) && numberValue > 0;
}
