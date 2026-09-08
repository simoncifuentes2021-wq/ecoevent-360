"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardList, PackageCheck, Plus, Search, SlidersHorizontal, Trash2, X } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import {
  LogisticsAttentionNote,
  LogisticsOrdersOverview,
  logisticsStatusLabels
} from "@/components/logistics/LogisticsOrdersOverview";
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
import type { LogisticsOrder, LogisticsOrderCreate, LogisticsOrderItemCreate, LogisticsOrderStatus } from "@/types/logistics-order";
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

type ItemFormRow = {
  item_id: string;
  quantity_requested: string;
  notes: string;
};

type QuickOrderFormState = {
  event_id: string;
  title: string;
  warehouse_id: string;
  assigned_operator_id: string;
  description: string;
  delivery_zone: string;
  delivery_notes: string;
  items: ItemFormRow[];
};

export default function AdminLogisticsOrdersPage() {
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
      const [orderResponse, eventResponse, warehouseResponse, allProducts, allStock, userResponse] = await Promise.all([
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
      setOperators(userResponse.items.filter((user) => user.role === "LOGISTICS_OPERATOR" && user.is_active));
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
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
          <PageHeader
            eyebrow="Administracion"
            title="Pedidos logisticos"
            description="Bandeja global del flujo logistico nuevo: reserva, preparacion, salida, entrega, resultados y cierre."
          />
          <Button onClick={() => setFormOpen(true)} type="button">
            <Plus className="h-4 w-4" />
            Crear pedido rapido
          </Button>
        </div>

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Metric icon={ClipboardList} label="Pedidos totales" value={orders.length} helper="Todos los registros" />
          <Metric icon={PackageCheck} label="En operación" value={orders.filter((order) => !["CLOSED", "CANCELLED"].includes(order.status)).length} helper="Requieren seguimiento" />
          <Metric icon={AlertTriangle} label="Con diferencias" value={orders.filter((order) => order.status === "WITH_DIFFERENCES").length} helper="Necesitan revisión" warning />
          <Metric icon={CheckCircle2} label="Cerrados" value={orders.filter((order) => order.status === "CLOSED").length} helper="Flujos completados" />
        </section>

        <LogisticsAttentionNote count={orders.filter((order) => ["INSUFFICIENT_STOCK", "WITH_DIFFERENCES", "OBSERVED"].includes(order.status)).length} />

        <Card className="border-slate-200 shadow-sm">
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
                <SlidersHorizontal className="h-4 w-4 text-emerald-700" />
                Buscar y filtrar
              </div>
              <span className="text-xs font-semibold text-slate-500">{filtered.length} de {orders.length}</span>
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
              <Button
                disabled={!q && !status}
                type="button"
                variant="ghost"
                onClick={() => { setQ(""); setStatus(""); }}
              >
                <X className="h-4 w-4" /> Limpiar
              </Button>
            </div>
          </CardContent>
        </Card>

        <LogisticsOrdersOverview
          orders={filtered}
          emptyTitle="Sin pedidos logisticos"
          emptyDescription="Crea un pedido rapido desde esta pantalla o desde la pestana Logistica de un evento."
          error={error}
          loading={loading}
          onRetry={load}
          hrefFor={(order) => `/admin/logistica/pedidos/${order.id}`}
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
  const [form, setForm] = useState<QuickOrderFormState>({
    event_id: events[0]?.id || "",
    title: "",
    warehouse_id: warehouses[0]?.id || "",
    assigned_operator_id: operators[0]?.id || "",
    description: "",
    delivery_zone: "",
    delivery_notes: "",
    items: []
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [eventQuery, setEventQuery] = useState("");
  const [productQuery, setProductQuery] = useState("");
  const duplicateProductId = findDuplicateProductId(form.items);
  const selectedProductIds = useMemo(() => new Set(form.items.map((row) => row.item_id)), [form.items]);
  const selectedEvent = events.find((event) => event.id === form.event_id);
  const filteredEvents = useMemo(() => {
    const query = eventQuery.trim().toLowerCase();
    if (!query) return events.slice(0, 8);
    return events
      .filter((event) =>
        [event.name, event.client?.business_name, event.location_name, event.city, event.status]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(query))
      )
      .slice(0, 8);
  }, [eventQuery, events]);
  const total = useMemo(
    () =>
      form.items.reduce((sum, row) => {
        const product = products.find((item) => item.id === row.item_id);
        return sum + Number(product?.unit_price || 0) * Number(row.quantity_requested || 0);
      }, 0),
    [form.items, products]
  );
  const validationMessage = getValidationMessage(form, duplicateProductId);
  const valid =
    form.event_id &&
    form.title.trim().length > 0 &&
    form.warehouse_id &&
    form.assigned_operator_id &&
    form.items.length > 0 &&
    form.items.every((row) => row.item_id && isPositiveInteger(row.quantity_requested)) &&
    !duplicateProductId;

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form.event_id, {
        title: form.title.trim(),
        warehouse_id: form.warehouse_id,
        assigned_operator_id: form.assigned_operator_id,
        description: form.description || null,
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

  function updateRow(index: number, data: Partial<ItemFormRow>) {
    setForm((current) => ({
      ...current,
      items: current.items.map((row, rowIndex) => (rowIndex === index ? { ...row, ...data } : row))
    }));
  }

  function addProduct(product: InventoryItem) {
    if (selectedProductIds.has(product.id)) {
      setError("Este producto ya fue agregado al pedido.");
      return;
    }
    setError(null);
    setForm((current) => ({
      ...current,
      items: [...current.items, { item_id: product.id, quantity_requested: "1", notes: "" }]
    }));
    setProductQuery("");
  }

  return (
    <ModalShell
      description="Selecciona evento, bodega, operador y productos en una sola vista."
      onClose={onClose}
      size="lg"
      title="Crear pedido logistico rapido"
    >
      <form className="space-y-5" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}

        <section className="space-y-3 rounded-lg border bg-slate-50 p-4">
          <div>
            <h3 className="font-semibold">Evento</h3>
            <p className="text-sm text-muted-foreground">Busca por nombre, cliente, ciudad o estado.</p>
          </div>
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <Input
              className="pl-9"
              placeholder="Buscar evento"
              value={eventQuery}
              onChange={(event) => setEventQuery(event.target.value)}
            />
          </div>
          <div className="grid max-h-56 gap-2 overflow-y-auto pr-1">
            {filteredEvents.length === 0 ? (
              <div className="rounded-md border border-dashed bg-white p-4 text-sm text-muted-foreground">
                No encontramos eventos con esa busqueda.
              </div>
            ) : (
              filteredEvents.map((event) => (
                <button
                  className={`rounded-md border bg-white p-3 text-left transition hover:border-primary hover:bg-emerald-50 ${form.event_id === event.id ? "border-primary bg-emerald-50" : ""}`}
                  key={event.id}
                  onClick={() => {
                    setForm((current) => ({ ...current, event_id: event.id }));
                    setEventQuery(event.name);
                  }}
                  type="button"
                >
                  <p className="font-semibold">{event.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {event.client?.business_name || "Sin cliente"} · {formatDate(event.start_date)} · {event.city || event.location_name || "Sin ubicacion"}
                  </p>
                </button>
              ))
            )}
          </div>
          {selectedEvent ? (
            <div className="rounded-md border bg-white p-3 text-sm">
              Evento seleccionado: <span className="font-semibold">{selectedEvent.name}</span>
            </div>
          ) : null}
        </section>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Titulo del pedido
            <Input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Zona/lugar de entrega
            <Input value={form.delivery_zone} onChange={(event) => setForm({ ...form, delivery_zone: event.target.value })} />
          </label>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Bodega de origen
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
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Observaciones de entrega
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={form.delivery_notes} onChange={(event) => setForm({ ...form, delivery_notes: event.target.value })} />
        </label>

        <section className="space-y-3">
          <div>
            <h3 className="font-semibold">Productos</h3>
            <p className="text-sm text-muted-foreground">Agrega productos desde la lista y ajusta cantidades.</p>
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
            <h4 className="font-semibold">Productos del pedido</h4>
            {form.items.map((row, index) => {
              const product = products.find((item) => item.id === row.item_id);
              const rowTotal = Number(row.quantity_requested || 0) * Number(product?.unit_price || 0);
              const isDuplicate = Boolean(row.item_id && row.item_id === duplicateProductId);
              return (
                <Card className={isDuplicate ? "border-amber-300 bg-amber-50/40" : ""} key={row.item_id || index}>
                  <CardContent className="space-y-3">
                    <div className="grid gap-3 md:grid-cols-[minmax(220px,1fr)_120px_90px_120px_120px_44px] md:items-center">
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{product?.name || "Producto no seleccionado"}</p>
                        <p className="text-xs text-muted-foreground">{product?.sku || "Sin SKU"}</p>
                      </div>
                      <label className="grid gap-2 text-sm font-semibold">
                        Cantidad
                        <Input min={1} step="1" type="number" value={row.quantity_requested} onChange={(event) => updateRow(index, { quantity_requested: event.target.value })} />
                      </label>
                      <Info label="Unidad" value={product?.unit || "-"} />
                      <Info label="Valor unitario" value={money(product?.unit_price || 0)} />
                      <Info label="Total" value={money(rowTotal)} />
                      <Button aria-label="Eliminar producto" type="button" variant="ghost" onClick={() => setForm({ ...form, items: form.items.filter((_, rowIndex) => rowIndex !== index) })}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <label className="grid gap-2 text-sm font-semibold">
                      Nota del producto
                      <Input value={row.notes} onChange={(event) => updateRow(index, { notes: event.target.value })} />
                    </label>
                    {isDuplicate ? <p className="text-sm font-semibold text-amber-700">Este producto ya fue agregado al pedido.</p> : null}
                  </CardContent>
                </Card>
              );
            })}
            {form.items.length === 0 ? (
              <div className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
                Aun no agregaste productos al pedido.
              </div>
            ) : null}
          </div>
        </section>

        <div className="rounded-lg border bg-slate-50 p-4 text-right">
          <p className="text-sm text-muted-foreground">Total estimado del pedido</p>
          <p className="text-2xl font-bold">{money(total)}</p>
        </div>
        {!valid ? <p className="text-sm font-semibold text-amber-700">{validationMessage}</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Crear pedido"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 text-sm">
      <p className="text-muted-foreground">{label}</p>
      <p className="truncate font-semibold">{value}</p>
    </div>
  );
}

function findDuplicateProductId(items: LogisticsOrderItemCreate[] | ItemFormRow[]) {
  const seen = new Set<string>();
  for (const row of items) {
    if (!row.item_id) continue;
    if (seen.has(row.item_id)) return row.item_id;
    seen.add(row.item_id);
  }
  return "";
}

function getValidationMessage(form: QuickOrderFormState, duplicateProductId: string) {
  if (!form.event_id) return "Debes seleccionar un evento.";
  if (!form.title.trim()) return "Debes ingresar un titulo.";
  if (!form.warehouse_id) return "Debes seleccionar una bodega.";
  if (!form.assigned_operator_id) return "Debes seleccionar un operador logistico.";
  if (form.items.length === 0) return "Debes agregar al menos un producto.";
  if (form.items.some((row) => !isPositiveInteger(row.quantity_requested))) {
    return "La cantidad debe ser un numero entero mayor a 0.";
  }
  if (duplicateProductId) return "Este producto ya fue agregado al pedido.";
  return "Revisa los datos antes de guardar.";
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("es-CL", { timeZone: "America/Santiago" });
}

function isPositiveInteger(value: string | number) {
  const numberValue = Number(value);
  return Number.isInteger(numberValue) && numberValue > 0;
}

function Metric({
  icon: Icon,
  label,
  value,
  helper,
  warning = false
}: {
  icon: typeof ClipboardList;
  label: string;
  value: number;
  helper: string;
  warning?: boolean;
}) {
  return (
    <Card className={warning ? "border-amber-200 bg-amber-50/40" : "border-slate-200"}>
      <CardContent className="flex items-center gap-4 p-4">
        <span className={`grid h-11 w-11 shrink-0 place-items-center rounded-xl ${warning ? "bg-amber-100 text-amber-700" : "bg-emerald-50 text-emerald-700"}`}>
          <Icon className="h-5 w-5" />
        </span>
        <div>
          <p className="text-sm font-semibold text-slate-600">{label}</p>
          <p className="text-2xl font-extrabold text-slate-950">{value}</p>
          <p className="text-xs text-slate-400">{helper}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}
