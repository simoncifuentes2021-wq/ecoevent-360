"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Boxes, ClipboardList, Edit, PackageSearch, Plus, Warehouse } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import { getInventoryItems } from "@/lib/api/inventory";
import { createStockMovement, getStockBalances } from "@/lib/api/stock";
import { getWarehouses } from "@/lib/api/warehouses";
import type { InventoryItem, InventoryItemType } from "@/types/inventory";
import type { StockBalance, StockBalanceCreate } from "@/types/stock";
import type { Warehouse as WarehouseType } from "@/types/warehouse";

const limit = 20;

const itemTypeLabels: Record<InventoryItemType, string> = {
  RETURNABLE: "Retornable",
  CONSUMABLE: "Consumible",
  PARTIAL_CONSUMABLE: "Parcial",
  DISPOSABLE: "Desechable"
};

type StockFormState = {
  warehouse_id: string;
  item_id: string;
  quantity_on_hand: string;
  quantity_reserved: string;
  quantity_damaged: string;
  reason: string;
};

type StockFormSubmit = StockBalanceCreate & {
  reason?: string;
};

export default function AdminStockPage() {
  const [stock, setStock] = useState<StockBalance[]>([]);
  const [warehouses, setWarehouses] = useState<WarehouseType[]>([]);
  const [products, setProducts] = useState<InventoryItem[]>([]);
  const [q, setQ] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [lowStock, setLowStock] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formTarget, setFormTarget] = useState<StockBalance | null | undefined>(undefined);
  const loadSeq = useRef(0);

  const loadStock = useCallback(async () => {
    const seq = loadSeq.current + 1;
    loadSeq.current = seq;
    setLoading(true);
    setError(null);
    try {
      const response = await getStockBalances({
        q: q || undefined,
        warehouse_id: warehouseId || undefined,
        low_stock: lowStock || undefined,
        page,
        limit
      });
      if (seq !== loadSeq.current) return;
      setStock(response.items);
      setTotal(response.total);
    } catch (err) {
      if (seq !== loadSeq.current) return;
      setError(err instanceof Error ? err.message : "No pudimos cargar el stock.");
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [lowStock, page, q, warehouseId]);

  const loadOptions = useCallback(async () => {
    const [warehouseResponse, productResponse] = await Promise.all([
      getWarehouses({ is_active: true, limit: 100 }),
      getInventoryItems({ is_active: true, limit: 100 })
    ]);
    setWarehouses(warehouseResponse.items);
    setProducts(productResponse.items);
  }, []);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const warehouseFromQuery = params.get("warehouse_id");
    if (warehouseFromQuery) setWarehouseId(warehouseFromQuery);
  }, []);

  useEffect(() => {
    void loadStock();
  }, [loadStock]);

  async function saveStock(data: StockFormSubmit) {
    if (formTarget) {
      await createStockMovement({
        warehouse_id: formTarget.warehouse_id,
        item_id: formTarget.item_id,
        movement_type: "CORRECTION",
        quantity: correctionQuantity(formTarget, data),
        quantity_on_hand: data.quantity_on_hand,
        quantity_reserved: data.quantity_reserved,
        quantity_damaged: data.quantity_damaged,
        reason: data.reason || "Correccion manual de stock"
      });
    } else {
      await createStockMovement({
        warehouse_id: data.warehouse_id,
        item_id: data.item_id,
        movement_type: "INITIAL_STOCK",
        quantity: data.quantity_on_hand || 0,
        quantity_reserved: data.quantity_reserved,
        quantity_damaged: data.quantity_damaged,
        reason: "Carga inicial de stock"
      });
    }
    setFormTarget(undefined);
    await loadStock();
  }

  const metrics = useMemo(() => {
    const warehouseIds = new Set(stock.map((item) => item.warehouse_id));
    return [
      {
        title: "Total productos en stock",
        value: stock.length.toLocaleString("es-CL"),
        icon: PackageSearch
      },
      {
        title: "Total bodegas con stock",
        value: warehouseIds.size.toLocaleString("es-CL"),
        icon: Warehouse
      },
      {
        title: "Productos con bajo stock",
        value: stock.filter((item) => item.is_low_stock).length.toLocaleString("es-CL"),
        icon: Boxes
      },
      {
        title: "Valor estimado de inventario",
        value: money(stock.reduce((sum, item) => sum + Number(item.estimated_stock_value || 0), 0)),
        icon: Boxes
      }
    ];
  }, [stock]);

  const columns: DataTableColumn<StockBalance>[] = [
    {
      key: "item",
      header: "Producto",
      cell: (item) => (
        <div>
          <p className="font-semibold">{item.item_name}</p>
          <p className="text-xs text-muted-foreground">{item.unit || "Sin unidad"}</p>
        </div>
      )
    },
    { key: "item_type", header: "Tipo", cell: (item) => itemTypeLabels[item.item_type] },
    { key: "warehouse", header: "Bodega", cell: (item) => item.warehouse_name },
    { key: "quantity_on_hand", header: "Total", cell: (item) => quantity(item.quantity_on_hand) },
    { key: "quantity_reserved", header: "Reservado", cell: (item) => quantity(item.quantity_reserved) },
    { key: "quantity_damaged", header: "Danado", cell: (item) => quantity(item.quantity_damaged) },
    { key: "available_quantity", header: "Disponible", cell: (item) => quantity(item.available_quantity) },
    { key: "min_stock", header: "Stock minimo", cell: (item) => quantity(item.min_stock) },
    { key: "unit_price", header: "Valor unitario", cell: (item) => money(item.unit_price) },
    { key: "estimated_stock_value", header: "Valor estimado", cell: (item) => money(item.estimated_stock_value) },
    {
      key: "is_low_stock",
      header: "Estado",
      cell: (item) => <Badge tone={item.is_low_stock ? "warning" : "success"}>{item.is_low_stock ? "Bajo" : "OK"}</Badge>
    }
  ];

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Administracion"
          title="Stock"
          description="Balance actual por bodega y producto. Las entradas, salidas, danos y perdidas se registran desde Movimientos."
          actions={
            <div className="flex flex-wrap justify-end gap-2">
              <Link
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90"
                href="/admin/stock/movimientos"
              >
                <ClipboardList className="h-4 w-4" />
                Registrar movimiento
              </Link>
              <Button onClick={() => setFormTarget(null)} type="button" variant="secondary">
                <Plus className="h-4 w-4" />
                Stock inicial
              </Button>
            </div>
          }
        />

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <Card key={metric.title}>
                <CardContent className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">{metric.title}</p>
                    <p className="mt-1 text-2xl font-bold">{metric.value}</p>
                  </div>
                  <span className="grid h-11 w-11 place-items-center rounded-md bg-emerald-50 text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-[220px_1fr_180px]">
          <select
            className="h-10 rounded-md border bg-white px-3 text-sm"
            value={warehouseId}
            onChange={(event) => {
              setWarehouseId(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Todas las bodegas</option>
            {warehouses.map((warehouse) => (
              <option key={warehouse.id} value={warehouse.id}>
                {warehouse.name}
              </option>
            ))}
          </select>
          <Input
            placeholder="Buscar producto, SKU o bodega"
            value={q}
            onChange={(event) => {
              setQ(event.target.value);
              setPage(1);
            }}
          />
          <select
            className="h-10 rounded-md border bg-white px-3 text-sm"
            value={lowStock}
            onChange={(event) => {
              setLowStock(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Todo stock</option>
            <option value="true">Bajo stock</option>
            <option value="false">Stock OK</option>
          </select>
        </div>

        <DataTable
          actions={(item) => (
            <div className="flex justify-end gap-2">
              <Button size="sm" title="Corregir balance" type="button" variant="secondary" onClick={() => setFormTarget(item)}>
                <Edit className="h-4 w-4" />
              </Button>
            </div>
          )}
          columns={columns}
          data={stock}
          emptyTitle="Sin stock registrado"
          emptyDescription="Registra stock inicial o crea un movimiento de entrada para comenzar el historial."
          error={error}
          getRowKey={(item) => item.id}
          limit={limit}
          loading={loading}
          onPageChange={setPage}
          page={page}
          total={total}
        />

        {formTarget !== undefined ? (
          <StockFormModal
            initialData={formTarget || undefined}
            products={products}
            warehouses={warehouses}
            onClose={() => setFormTarget(undefined)}
            onSubmit={saveStock}
          />
        ) : null}
      </div>
    </RoleGuard>
  );
}

function StockFormModal({
  initialData,
  products,
  warehouses,
  onClose,
  onSubmit
}: {
  initialData?: StockBalance;
  products: InventoryItem[];
  warehouses: WarehouseType[];
  onClose: () => void;
  onSubmit: (data: StockFormSubmit) => Promise<void>;
}) {
  const [form, setForm] = useState<StockFormState>({
    warehouse_id: initialData?.warehouse_id || warehouses[0]?.id || "",
    item_id: initialData?.item_id || products[0]?.id || "",
    quantity_on_hand: initialData ? String(initialData.quantity_on_hand) : "0",
    quantity_reserved: initialData ? String(initialData.quantity_reserved) : "0",
    quantity_damaged: initialData ? String(initialData.quantity_damaged) : "0",
    reason: ""
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selectedProduct = products.find((product) => product.id === form.item_id);
  const onHand = numberOrNull(form.quantity_on_hand);
  const reserved = numberOrNull(form.quantity_reserved);
  const damaged = numberOrNull(form.quantity_damaged);
  const available =
    onHand !== null && reserved !== null && damaged !== null ? onHand - reserved - damaged : null;
  const valid =
    Boolean(form.warehouse_id) &&
    Boolean(form.item_id) &&
    onHand !== null &&
    reserved !== null &&
    damaged !== null &&
    available !== null &&
    reserved <= onHand &&
    damaged <= onHand &&
    available >= 0 &&
    (!initialData || form.reason.trim().length > 0) &&
    (Boolean(initialData) || onHand > 0);
  const validationMessage = getStockFormMessage({
    initialData: Boolean(initialData),
    warehouseId: form.warehouse_id,
    itemId: form.item_id,
    onHand,
    reserved,
    damaged,
    available,
    reason: form.reason
  });

  async function submit() {
    if (!valid || onHand === null || reserved === null || damaged === null) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        warehouse_id: form.warehouse_id,
        item_id: form.item_id,
        quantity_on_hand: onHand,
        quantity_reserved: reserved,
        quantity_damaged: damaged,
        reason: form.reason.trim() || undefined
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo guardar el stock.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={initialData ? "Corregir balance de stock" : "Registrar stock inicial"}
      description={
        initialData
          ? "Ajusta el balance actual y deja una correccion registrada en movimientos."
          : "Crea el balance inicial de un producto en una bodega. Para sumar o restar stock despues, usa Movimientos."
      }
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Bodega
            <select
              className="h-10 rounded-md border bg-white px-3 text-sm"
              disabled={Boolean(initialData)}
              value={form.warehouse_id}
              onChange={(event) => setForm({ ...form, warehouse_id: event.target.value })}
            >
              <option value="">Seleccionar bodega</option>
              {warehouses.map((warehouse) => (
                <option key={warehouse.id} value={warehouse.id}>
                  {warehouse.name}
                </option>
              ))}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Producto
            <select
              className="h-10 rounded-md border bg-white px-3 text-sm"
              disabled={Boolean(initialData)}
              value={form.item_id}
              onChange={(event) => setForm({ ...form, item_id: event.target.value })}
            >
              <option value="">Seleccionar producto</option>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="grid gap-2 text-sm font-semibold">
            Stock fisico actual
            <Input min={0} step="0.01" type="number" value={form.quantity_on_hand} onChange={(event) => setForm({ ...form, quantity_on_hand: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Reservado
            <Input min={0} step="0.01" type="number" value={form.quantity_reserved} onChange={(event) => setForm({ ...form, quantity_reserved: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Danado / no disponible
            <Input min={0} step="0.01" type="number" value={form.quantity_damaged} onChange={(event) => setForm({ ...form, quantity_damaged: event.target.value })} />
          </label>
        </div>
        <Card>
          <CardContent className="grid gap-2 text-sm md:grid-cols-3">
            <div>
              <p className="text-muted-foreground">Disponible</p>
              <p className="text-lg font-bold">{available === null ? "-" : quantity(available)}</p>
              <p className="text-xs text-muted-foreground">Fisico - reservado - danado</p>
            </div>
            <div>
              <p className="text-muted-foreground">Unidad</p>
              <p className="font-semibold">{selectedProduct?.unit || "-"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Valor unitario</p>
              <p className="font-semibold">{money(selectedProduct?.unit_price ?? 0)}</p>
            </div>
          </CardContent>
        </Card>
        {initialData ? (
          <label className="grid gap-2 text-sm font-semibold">
            Motivo de correccion
            <textarea
              className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
              value={form.reason}
              onChange={(event) => setForm({ ...form, reason: event.target.value })}
            />
          </label>
        ) : null}
        {!valid ? (
          <p className="text-sm font-semibold text-amber-700">
            {validationMessage}
          </p>
        ) : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>
            Cancelar
          </Button>
          <Button disabled={!valid || saving} type="submit">
            {saving ? "Guardando..." : "Guardar"}
          </Button>
        </div>
      </form>
    </ModalShell>
  );
}

function numberOrNull(value: string) {
  if (value === "") return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function quantity(value: string | number | null) {
  return Number(value || 0).toLocaleString("es-CL");
}

function money(value: string | number | null) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}

function getStockFormMessage({
  initialData,
  warehouseId,
  itemId,
  onHand,
  reserved,
  damaged,
  available,
  reason
}: {
  initialData: boolean;
  warehouseId: string;
  itemId: string;
  onHand: number | null;
  reserved: number | null;
  damaged: number | null;
  available: number | null;
  reason: string;
}) {
  if (!warehouseId || !itemId) return "Selecciona una bodega y un producto.";
  if (onHand === null || reserved === null || damaged === null) {
    return "Las cantidades deben ser numeros validos y no pueden ser negativas.";
  }
  if (reserved > onHand) return "El reservado no puede ser mayor que el stock fisico.";
  if (damaged > onHand) return "El danado no puede ser mayor que el stock fisico.";
  if (available !== null && available < 0) return "El disponible no puede quedar bajo cero.";
  if (!initialData && onHand <= 0) return "Para stock inicial, el stock fisico debe ser mayor a 0.";
  if (initialData && !reason.trim()) return "Las correcciones de balance requieren motivo.";
  return "Revisa los datos antes de guardar.";
}

function correctionQuantity(current: StockBalance, data: StockBalanceCreate) {
  return Math.max(
    Math.abs(Number(data.quantity_on_hand || 0) - Number(current.quantity_on_hand || 0)),
    Math.abs(Number(data.quantity_reserved || 0) - Number(current.quantity_reserved || 0)),
    Math.abs(Number(data.quantity_damaged || 0) - Number(current.quantity_damaged || 0)),
    1
  );
}
