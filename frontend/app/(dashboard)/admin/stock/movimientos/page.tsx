"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { FileImage, Plus } from "lucide-react";

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
import { ApiError } from "@/lib/api";
import { getInventoryItems } from "@/lib/api/inventory";
import { createStockMovement, getStockBalances, getStockMovements } from "@/lib/api/stock";
import { getWarehouses } from "@/lib/api/warehouses";
import type { InventoryItem } from "@/types/inventory";
import type { LogisticsEvidenceStage } from "@/types/logistics-evidence";
import type { StockBalance, StockMovement, StockMovementCreate, StockMovementType } from "@/types/stock";
import type { Warehouse } from "@/types/warehouse";

const limit = 20;

const movementTypes: StockMovementType[] = [
  "INITIAL_STOCK",
  "ADJUSTMENT_IN",
  "ADJUSTMENT_OUT",
  "DAMAGE",
  "LOSS",
  "RECOVER_DAMAGED"
];

const movementTypeLabels: Record<StockMovementType, string> = {
  INITIAL_STOCK: "Stock inicial",
  ADJUSTMENT_IN: "Entrada manual",
  ADJUSTMENT_OUT: "Salida manual",
  DAMAGE: "Dano",
  LOSS: "Perdida",
  RECOVER_DAMAGED: "Recupera danado",
  CORRECTION: "Correccion",
  PURCHASE_IN: "Compra",
  RESERVE: "Reserva",
  UNRESERVE: "Libera reserva",
  OUT_TO_EVENT: "Salida a evento",
  RETURN_FROM_EVENT: "Retorno desde evento"
};

type MovementFormState = {
  warehouse_id: string;
  item_id: string;
  movement_type: StockMovementType;
  quantity: string;
  reason: string;
  notes: string;
};

export default function StockMovementsPage() {
  const [movements, setMovements] = useState<StockMovement[]>([]);
  const [warehouses, setWarehouses] = useState<Warehouse[]>([]);
  const [products, setProducts] = useState<InventoryItem[]>([]);
  const [stock, setStock] = useState<StockBalance[]>([]);
  const [warehouseId, setWarehouseId] = useState("");
  const [itemId, setItemId] = useState("");
  const [movementType, setMovementType] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [evidenceTarget, setEvidenceTarget] = useState<StockMovement | null>(null);
  const loadSeq = useRef(0);

  const loadMovements = useCallback(async () => {
    const seq = loadSeq.current + 1;
    loadSeq.current = seq;
    setLoading(true);
    setError(null);
    try {
      const response = await getStockMovements({
        warehouse_id: warehouseId || undefined,
        item_id: itemId || undefined,
        movement_type: movementType || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
        page,
        limit
      });
      if (seq !== loadSeq.current) return;
      setMovements(response.items);
      setTotal(response.total);
    } catch (err) {
      if (seq !== loadSeq.current) return;
      setError(err instanceof Error ? err.message : "No pudimos cargar los movimientos.");
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [dateFrom, dateTo, itemId, movementType, page, warehouseId]);

  const loadOptions = useCallback(async () => {
    const [warehouseResponse, productResponse, stockResponse] = await Promise.all([
      getWarehouses({ is_active: true, limit: 100 }),
      getInventoryItems({ is_active: true, limit: 100 }),
      getStockBalances({ limit: 100 })
    ]);
    setWarehouses(warehouseResponse.items);
    setProducts(productResponse.items);
    setStock(stockResponse.items);
  }, []);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  useEffect(() => {
    void loadMovements();
  }, [loadMovements]);

  async function saveMovement(data: StockMovementCreate) {
    await createStockMovement(data);
    setFormOpen(false);
    await Promise.all([loadMovements(), loadOptions()]);
  }

  const columns: DataTableColumn<StockMovement>[] = [
    { key: "created_at", header: "Fecha", cell: (item) => new Date(item.created_at).toLocaleString("es-CL") },
    { key: "item", header: "Producto", cell: (item) => item.item_name },
    { key: "warehouse", header: "Bodega", cell: (item) => item.warehouse_name },
    {
      key: "movement_type",
      header: "Tipo movimiento",
      cell: (item) => <Badge tone={movementTone(item.movement_type)}>{movementTypeLabels[item.movement_type]}</Badge>
    },
    { key: "quantity", header: "Cantidad", cell: (item) => quantity(item.quantity) },
    { key: "previous_on_hand", header: "Stock anterior", cell: (item) => quantity(item.previous_quantity_on_hand) },
    { key: "new_on_hand", header: "Stock nuevo", cell: (item) => quantity(item.new_quantity_on_hand) },
    { key: "previous_damaged", header: "Danado anterior", cell: (item) => quantity(item.previous_quantity_damaged) },
    { key: "new_damaged", header: "Danado nuevo", cell: (item) => quantity(item.new_quantity_damaged) },
    { key: "created_by", header: "Usuario", cell: (item) => item.created_by_name || "-" },
    { key: "reason", header: "Motivo/observacion", cell: (item) => item.reason || item.notes || "-" }
  ];

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Stock"
          title="Movimientos de stock"
          description="Historial auditable de entradas, salidas, danos, perdidas y ajustes de inventario."
          actions={
            <Button onClick={() => setFormOpen(true)} type="button">
              <Plus className="h-4 w-4" />
              Crear movimiento
            </Button>
          }
        />

        <div className="grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-5">
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={warehouseId} onChange={(event) => { setWarehouseId(event.target.value); setPage(1); }}>
            <option value="">Todas las bodegas</option>
            {warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}
          </select>
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={itemId} onChange={(event) => { setItemId(event.target.value); setPage(1); }}>
            <option value="">Todos los productos</option>
            {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
          </select>
          <select className="h-10 rounded-md border bg-white px-3 text-sm" value={movementType} onChange={(event) => { setMovementType(event.target.value); setPage(1); }}>
            <option value="">Todos los tipos</option>
            {Object.entries(movementTypeLabels).map(([type, label]) => <option key={type} value={type}>{label}</option>)}
          </select>
          <Input type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} />
          <Input type="date" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} />
        </div>

        <DataTable
          columns={columns}
          data={movements}
          emptyTitle="Sin movimientos"
          emptyDescription="Registra un movimiento para comenzar el historial de stock."
          error={error}
          getRowKey={(item) => item.id}
          limit={limit}
          loading={loading}
          onPageChange={setPage}
          page={page}
          total={total}
          actions={(item) => (
            <Button size="sm" type="button" variant="secondary" onClick={() => setEvidenceTarget(item)}>
              <FileImage className="h-4 w-4" />
              Evidencias
            </Button>
          )}
        />

        {formOpen ? (
          <MovementFormModal
            products={products}
            stock={stock}
            warehouses={warehouses}
            onClose={() => setFormOpen(false)}
            onSubmit={saveMovement}
          />
        ) : null}

        {evidenceTarget ? (
          <ModalShell
            title="Evidencias del movimiento"
            description={`${evidenceTarget.item_name} - ${movementTypeLabels[evidenceTarget.movement_type]}`}
            onClose={() => setEvidenceTarget(null)}
          >
            <LogisticsEvidenceUploader
              stockMovementId={evidenceTarget.id}
              stage={stockMovementEvidenceStage(evidenceTarget.movement_type)}
              title="Evidencias del movimiento de stock"
              required={["DAMAGE", "LOSS", "CORRECTION"].includes(evidenceTarget.movement_type)}
            />
          </ModalShell>
        ) : null}
      </div>
    </RoleGuard>
  );
}

function MovementFormModal({
  products,
  stock,
  warehouses,
  onClose,
  onSubmit
}: {
  products: InventoryItem[];
  stock: StockBalance[];
  warehouses: Warehouse[];
  onClose: () => void;
  onSubmit: (data: StockMovementCreate) => Promise<void>;
}) {
  const [form, setForm] = useState<MovementFormState>({
    warehouse_id: warehouses[0]?.id || "",
    item_id: products[0]?.id || "",
    movement_type: "ADJUSTMENT_IN",
    quantity: "1",
    reason: "",
    notes: ""
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentStock = useMemo(
    () => stock.find((item) => item.warehouse_id === form.warehouse_id && item.item_id === form.item_id),
    [form.item_id, form.warehouse_id, stock]
  );
  const quantityValue = numberOrNull(form.quantity);
  const reasonRequired = ["DAMAGE", "LOSS", "CORRECTION"].includes(form.movement_type);
  const warning = movementWarning(form.movement_type, quantityValue, currentStock);
  const valid =
    Boolean(form.warehouse_id) &&
    Boolean(form.item_id) &&
    quantityValue !== null &&
    quantityValue > 0 &&
    !warning &&
    (!reasonRequired || form.reason.trim().length > 0 || form.notes.trim().length > 0);

  async function submit() {
    if (!valid || quantityValue === null) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        warehouse_id: form.warehouse_id,
        item_id: form.item_id,
        movement_type: form.movement_type,
        quantity: quantityValue,
        reason: form.reason || null,
        notes: form.notes || null
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo guardar el movimiento.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell title="Crear movimiento de stock" description="Todo movimiento actualiza stock y queda en historial." onClose={onClose}>
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Bodega
            <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.warehouse_id} onChange={(event) => setForm({ ...form, warehouse_id: event.target.value })}>
              <option value="">Seleccionar bodega</option>
              {warehouses.map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Producto
            <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.item_id} onChange={(event) => setForm({ ...form, item_id: event.target.value })}>
              <option value="">Seleccionar producto</option>
              {products.map((product) => <option key={product.id} value={product.id}>{product.name}</option>)}
            </select>
          </label>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Tipo de movimiento
            <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.movement_type} onChange={(event) => setForm({ ...form, movement_type: event.target.value as StockMovementType })}>
              {movementTypes.map((type) => <option key={type} value={type}>{movementTypeLabels[type]}</option>)}
            </select>
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Cantidad
            <Input min={0.01} step="0.01" type="number" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} />
          </label>
        </div>
        <Card>
          <CardContent className="grid gap-2 text-sm md:grid-cols-3">
            <div>
              <p className="text-muted-foreground">Stock actual</p>
              <p className="font-semibold">{quantity(currentStock?.quantity_on_hand ?? 0)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Disponible actual</p>
              <p className="font-semibold">{quantity(currentStock?.available_quantity ?? 0)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Danado actual</p>
              <p className="font-semibold">{quantity(currentStock?.quantity_damaged ?? 0)}</p>
            </div>
          </CardContent>
        </Card>
        <label className="grid gap-2 text-sm font-semibold">
          Motivo {reasonRequired ? "(obligatorio)" : ""}
          <Input value={form.reason} onChange={(event) => setForm({ ...form, reason: event.target.value })} />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Observaciones
          <textarea className="min-h-20 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
        {warning ? <p className="text-sm font-semibold text-amber-700">{warning}</p> : null}
        <div className="flex justify-end gap-2">
          <Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button>
          <Button disabled={!valid || saving} type="submit">{saving ? "Guardando..." : "Guardar"}</Button>
        </div>
      </form>
    </ModalShell>
  );
}

function movementWarning(type: StockMovementType, amount: number | null, stock?: StockBalance) {
  if (amount === null || amount <= 0) return "La cantidad debe ser mayor a 0.";
  const available = Number(stock?.available_quantity || 0);
  const damaged = Number(stock?.quantity_damaged || 0);
  if (["ADJUSTMENT_OUT", "LOSS", "DAMAGE"].includes(type) && amount > available) {
    return "Este movimiento dejaria el stock disponible en negativo.";
  }
  if (type === "RECOVER_DAMAGED" && amount > damaged) {
    return "No puedes recuperar mas unidades danadas que las registradas.";
  }
  return "";
}

function movementTone(type: StockMovementType) {
  if (["ADJUSTMENT_IN", "INITIAL_STOCK", "RECOVER_DAMAGED"].includes(type)) return "success";
  if (["DAMAGE", "LOSS", "ADJUSTMENT_OUT"].includes(type)) return "warning";
  return "neutral";
}

function stockMovementEvidenceStage(type: StockMovementType): LogisticsEvidenceStage {
  if (type === "DAMAGE") return "STOCK_DAMAGE";
  if (type === "LOSS") return "STOCK_LOSS";
  if (type === "CORRECTION") return "STOCK_CORRECTION";
  return "STOCK_ADJUSTMENT";
}

function numberOrNull(value: string) {
  if (value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function quantity(value: string | number | null | undefined) {
  return Number(value || 0).toLocaleString("es-CL");
}
