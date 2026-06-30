"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Eye, Plus, Search, Trash2 } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { getInventoryItems } from "@/lib/api/inventory";
import { createEventLogisticsOrder, getEventLogisticsOrders } from "@/lib/api/logistics-orders";
import { getUsers } from "@/lib/api/users";
import { getWarehouses } from "@/lib/api/warehouses";
import type { InventoryItem } from "@/types/inventory";
import type { LogisticsOrder, LogisticsOrderCreate, LogisticsOrderItemCreate, LogisticsOrderStatus } from "@/types/logistics-order";
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

type ItemFormRow = {
  item_id: string;
  quantity_requested: string;
  notes: string;
};

type OrderFormState = {
  title: string;
  warehouse_id: string;
  assigned_operator_id: string;
  description: string;
  delivery_zone: string;
  delivery_notes: string;
  items: ItemFormRow[];
};

export function LogisticsOrdersTab({ eventId, eventName, role }: { eventId: string; eventName?: string; role?: string | null }) {
  const [orders, setOrders] = useState<LogisticsOrder[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [products, setProducts] = useState<InventoryItem[]>([]);
  const [operators, setOperators] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const canCreate = role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
  const detailBaseHref = role === "SUPERVISOR" ? "/supervisor/logistica/pedidos" : "/admin/logistica/pedidos";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [orderResponse, warehouseResponse, productResponse, userResponse] = await Promise.all([
        getEventLogisticsOrders(eventId, { limit: 100 }),
        getWarehouses({ is_active: true, limit: 100 }),
        getInventoryItems({ is_active: true, limit: 100 }),
        getUsers({ role: "LOGISTICS_OPERATOR", is_active: true, limit: 100 })
      ]);
      setOrders(orderResponse.items);
      setWarehouses(warehouseResponse.items);
      setProducts(productResponse.items);
      setOperators(userResponse.items.filter((user) => user.role === "LOGISTICS_OPERATOR" && user.is_active));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los pedidos logisticos.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: LogisticsOrderCreate) {
    await createEventLogisticsOrder(eventId, data);
    setFormOpen(false);
    await load();
  }

  const columns: DataTableColumn<LogisticsOrder>[] = [
    { key: "title", header: "Pedido", cell: (order) => <span className="font-semibold">{order.title}</span> },
    { key: "warehouse", header: "Bodega", cell: (order) => order.warehouse?.name || "-" },
    { key: "operator", header: "Operador", cell: (order) => order.assigned_operator?.full_name || "-" },
    { key: "items", header: "Productos", cell: (order) => order.items.length },
    { key: "total", header: "Total estimado", cell: (order) => money(order.total_estimated_amount) },
    {
      key: "status",
      header: "Estado",
      cell: (order) => <Badge tone={order.status === "CANCELLED" ? "danger" : "success"}>{statusLabels[order.status]}</Badge>
    }
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
        <div>
          <h2 className="text-xl font-bold">Logistica</h2>
          <p className="text-sm text-muted-foreground">Pedidos logisticos nuevos con productos de inventario y precio historico.</p>
        </div>
        {canCreate ? (
          <Button onClick={() => setFormOpen(true)} type="button">
            <Plus className="h-4 w-4" />
            Crear pedido logistico
          </Button>
        ) : null}
      </div>
      <DataTable
        actions={(order) => (
          <Link href={`${detailBaseHref}/${order.id}`}>
            <Button size="sm" type="button" variant="secondary">
              <Eye className="h-4 w-4" />
            </Button>
          </Link>
        )}
        columns={columns}
        data={orders}
        emptyTitle="Sin pedidos logisticos"
        emptyDescription="Crea el primer pedido logistico para este evento."
        error={error}
        getRowKey={(order) => order.id}
        loading={loading}
      />
      {formOpen ? (
        <OrderFormModal
          eventName={eventName}
          operators={operators}
          products={products}
          warehouses={warehouses}
          onClose={() => setFormOpen(false)}
          onSubmit={submit}
        />
      ) : null}
    </div>
  );
}

function OrderFormModal({
  eventName,
  warehouses,
  products,
  operators,
  onClose,
  onSubmit
}: {
  eventName?: string;
  warehouses: Warehouse[];
  products: InventoryItem[];
  operators: User[];
  onClose: () => void;
  onSubmit: (data: LogisticsOrderCreate) => Promise<void>;
}) {
  const [form, setForm] = useState<OrderFormState>({
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
  const [productQuery, setProductQuery] = useState("");
  const duplicateProductId = findDuplicateProductId(form.items);
  const selectedProductIds = useMemo(() => new Set(form.items.map((row) => row.item_id)), [form.items]);
  const filteredProducts = useMemo(() => {
    const query = productQuery.trim().toLowerCase();
    return products
      .filter((product) => !selectedProductIds.has(product.id))
      .filter((product) => {
        if (!query) return true;
        return [product.name, product.sku, product.description, product.unit, product.item_type]
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
  const validationMessage = getValidationMessage(form, duplicateProductId);
  const valid =
    form.title.trim().length > 0 &&
    Boolean(form.warehouse_id) &&
    Boolean(form.assigned_operator_id) &&
    form.items.length > 0 &&
    form.items.every((row) => row.item_id && isPositiveInteger(row.quantity_requested)) &&
    !duplicateProductId;

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
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
      description="El evento viene desde esta vista. El backend copiara el precio actual como snapshot historico."
      onClose={onClose}
      size="lg"
      title="Crear pedido logistico"
    >
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}
        <div className="rounded-lg border bg-slate-50 p-4">
          <p className="text-sm text-muted-foreground">Evento</p>
          <p className="font-semibold">{eventName || "Evento actual"}</p>
        </div>
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
          Observaciones
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={form.delivery_notes} onChange={(event) => setForm({ ...form, delivery_notes: event.target.value })} />
        </label>

        <div className="space-y-4">
          <div>
            <div>
              <h3 className="font-semibold">Productos</h3>
              <p className="text-sm text-muted-foreground">Busca productos por nombre, SKU o tipo. El precio visible es referencia; el backend guarda el snapshot.</p>
            </div>
          </div>
          <Card>
            <CardContent className="space-y-3">
              <label className="grid gap-2 text-sm font-semibold">
                Buscar producto
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                  <Input
                    className="pl-9"
                    placeholder="Nombre, SKU, tipo o unidad"
                    value={productQuery}
                    onChange={(event) => setProductQuery(event.target.value)}
                  />
                </div>
              </label>
              <div className="grid max-h-72 gap-2 overflow-y-auto pr-1">
                {filteredProducts.length === 0 ? (
                  <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                    {products.length === form.items.length ? "Todos los productos disponibles ya fueron agregados." : "No encontramos productos con esa busqueda."}
                  </div>
                ) : (
                  filteredProducts.map((product) => (
                    <button
                      className="grid gap-3 rounded-md border bg-white p-3 text-left transition hover:border-primary hover:bg-emerald-50 md:grid-cols-[1fr_110px_120px_100px]"
                      key={product.id}
                      onClick={() => addProduct(product)}
                      type="button"
                    >
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{product.name}</p>
                        <p className="text-xs text-muted-foreground">{product.sku || "Sin SKU"}</p>
                      </div>
                      <Info label="Tipo" value={product.item_type} />
                      <Info label="Unidad" value={product.unit || "-"} />
                      <div className="flex items-center justify-between gap-2 md:justify-end">
                        <span className="text-sm font-semibold">{money(product.unit_price || 0)}</span>
                        <Plus className="h-4 w-4 text-primary" />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          <div className="space-y-3">
            <div>
              <h4 className="font-semibold">Productos del pedido</h4>
              <p className="text-sm text-muted-foreground">Ajusta la cantidad solicitada de cada producto agregado.</p>
            </div>
          {form.items.map((row, index) => {
            const product = products.find((item) => item.id === row.item_id);
            const rowTotal = Number(row.quantity_requested || 0) * Number(product?.unit_price || 0);
            const isDuplicate = Boolean(row.item_id && row.item_id === duplicateProductId);
            return (
              <Card className={isDuplicate ? "border-amber-300 bg-amber-50/40" : ""} key={index}>
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
                    <Button aria-label="Eliminar producto" disabled={form.items.length <= 1} type="button" variant="ghost" onClick={() => setForm({ ...form, items: form.items.filter((_, rowIndex) => rowIndex !== index) })}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="text-sm text-muted-foreground">Tipo: <span className="font-semibold text-slate-700">{product?.item_type || "-"}</span></div>
                  {isDuplicate ? <p className="text-sm font-semibold text-amber-700">Este producto ya fue agregado al pedido.</p> : null}
                </CardContent>
              </Card>
            );
          })}
            {form.items.length === 0 ? (
              <div className="rounded-lg border border-dashed p-5 text-sm text-muted-foreground">
                Aun no agregaste productos al pedido. Busca un producto arriba y presiona agregar.
              </div>
            ) : null}
          </div>
        </div>
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
    <div className="min-w-0">
      <p className="text-muted-foreground">{label}</p>
      <p className="truncate font-semibold">{value}</p>
    </div>
  );
}

function findDuplicateProductId(items: ItemFormRow[]) {
  const seen = new Set<string>();
  for (const row of items) {
    if (!row.item_id) continue;
    if (seen.has(row.item_id)) return row.item_id;
    seen.add(row.item_id);
  }
  return "";
}

function getValidationMessage(form: OrderFormState, duplicateProductId: string) {
  if (!form.title.trim()) return "Debes ingresar un titulo.";
  if (!form.warehouse_id) return "Debes seleccionar una bodega.";
  if (!form.assigned_operator_id) return "Debes seleccionar un operador logistico.";
  if (form.items.length === 0) return "Debes agregar al menos un producto.";
  if (form.items.some((row) => !row.item_id)) return "Debes seleccionar un producto en cada fila.";
  if (form.items.some((row) => !isPositiveInteger(row.quantity_requested))) {
    return "La cantidad debe ser un numero entero mayor a 0.";
  }
  if (duplicateProductId) return "Este producto ya fue agregado al pedido.";
  return "Revisa los datos antes de guardar.";
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}

function isPositiveInteger(value: string | number) {
  const numberValue = Number(value);
  return Number.isInteger(numberValue) && numberValue > 0;
}
