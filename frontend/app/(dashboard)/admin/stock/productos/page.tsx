"use client";

import { useCallback, useEffect, useState } from "react";
import { Edit, PackageSearch, Power, Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { ErrorState } from "@/components/common/ErrorState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { StatusBadge } from "@/components/common/StatusBadge";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api";
import {
  createInventoryItem,
  deactivateInventoryItem,
  getInventoryItems,
  updateInventoryItem
} from "@/lib/api/inventory";
import type { InventoryItem, InventoryItemCreate, InventoryItemType } from "@/types/inventory";

const limit = 20;

const itemTypeLabels: Record<InventoryItemType, string> = {
  RETURNABLE: "Retornable",
  CONSUMABLE: "Consumible",
  PARTIAL_CONSUMABLE: "Parcialmente consumible",
  DISPOSABLE: "Desechable"
};

const itemTypes: InventoryItemType[] = [
  "RETURNABLE",
  "CONSUMABLE",
  "PARTIAL_CONSUMABLE",
  "DISPOSABLE"
];

type ProductFormState = {
  sku: string;
  name: string;
  description: string;
  item_type: InventoryItemType;
  return_required: boolean;
  unit: string;
  unit_price: string;
  replacement_cost: string;
  min_stock: string;
  is_active: boolean;
};

export default function AdminInventoryProductsPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [q, setQ] = useState("");
  const [itemType, setItemType] = useState("");
  const [isActive, setIsActive] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formTarget, setFormTarget] = useState<InventoryItem | null | undefined>(undefined);
  const [deactivating, setDeactivating] = useState<InventoryItem | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getInventoryItems({
        q: q || undefined,
        item_type: itemType || undefined,
        is_active: isActive || undefined,
        page,
        limit
      });
      setItems(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los productos.");
    } finally {
      setLoading(false);
    }
  }, [isActive, itemType, page, q]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveProduct(data: InventoryItemCreate & { is_active?: boolean }) {
    if (formTarget) {
      await updateInventoryItem(formTarget.id, data);
    } else {
      await createInventoryItem(data);
    }
    setFormTarget(undefined);
    await load();
  }

  async function confirmDeactivate() {
    if (!deactivating) return;
    await deactivateInventoryItem(deactivating.id);
    setDeactivating(null);
    await load();
  }

  const columns: DataTableColumn<InventoryItem>[] = [
    {
      key: "name",
      header: "Producto",
      cell: (item) => (
        <div>
          <p className="font-semibold">{item.name}</p>
          <p className="text-xs text-slate-500">{item.sku || "Sin SKU"}</p>
        </div>
      )
    },
    {
      key: "item_type",
      header: "Tipo",
      cell: (item) => <ItemTypeBadge type={item.item_type} />
    },
    { key: "unit", header: "Unidad", cell: (item) => item.unit || "-" },
    {
      key: "unit_price",
      header: "Valor unitario actual",
      cell: (item) => money(item.unit_price)
    },
    {
      key: "replacement_cost",
      header: "Costo reposicion",
      cell: (item) => money(item.replacement_cost)
    },
    { key: "min_stock", header: "Stock minimo", cell: (item) => numberValue(item.min_stock) },
    {
      key: "return_required",
      header: "Devolucion",
      cell: (item) => item.return_required ? "Requerida" : "No requerida"
    },
    {
      key: "is_active",
      header: "Estado",
      cell: (item) => <StatusBadge status={item.is_active ? "ACTIVE" : "INACTIVE"} />
    }
  ];

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Productos de inventario"
          description="Catalogo base para futuras existencias, bodegas y pedidos logisticos."
          actions={
            <Button onClick={() => setFormTarget(null)} type="button">
              <Plus className="h-4 w-4" />
              Crear producto
            </Button>
          }
        />
        <div className="grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-[1fr_220px_180px]">
          <Input
            placeholder="Buscar por nombre, SKU o descripcion"
            value={q}
            onChange={(event) => {
              setQ(event.target.value);
              setPage(1);
            }}
          />
          <select
            className="h-10 rounded-md border bg-white px-3 text-sm"
            value={itemType}
            onChange={(event) => {
              setItemType(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos los tipos</option>
            {itemTypes.map((type) => (
              <option key={type} value={type}>
                {itemTypeLabels[type]}
              </option>
            ))}
          </select>
          <select
            className="h-10 rounded-md border bg-white px-3 text-sm"
            value={isActive}
            onChange={(event) => {
              setIsActive(event.target.value);
              setPage(1);
            }}
          >
            <option value="">Todos</option>
            <option value="true">Activos</option>
            <option value="false">Inactivos</option>
          </select>
        </div>
        <DataTable
          actions={(item) => (
            <div className="flex justify-end gap-2">
              <Button size="sm" type="button" variant="secondary" onClick={() => setFormTarget(item)}>
                <Edit className="h-4 w-4" />
              </Button>
              {item.is_active ? (
                <Button size="sm" type="button" variant="ghost" onClick={() => setDeactivating(item)}>
                  <Power className="h-4 w-4" />
                </Button>
              ) : null}
            </div>
          )}
          columns={columns}
          data={items}
          emptyTitle="Sin productos de inventario"
          emptyDescription="Crea el primer producto para preparar el catalogo logistico."
          error={error}
          getRowKey={(item) => item.id}
          limit={limit}
          loading={loading}
          onPageChange={setPage}
          page={page}
          total={total}
        />
        {formTarget !== undefined ? (
          <ProductFormModal
            initialData={formTarget || undefined}
            onClose={() => setFormTarget(undefined)}
            onSubmit={saveProduct}
          />
        ) : null}
        <ConfirmDialog
          description={`El producto ${deactivating?.name || ""} quedara inactivo, pero no se eliminara fisicamente.`}
          open={Boolean(deactivating)}
          title="Desactivar producto"
          onClose={() => setDeactivating(null)}
          onConfirm={confirmDeactivate}
        />
      </div>
    </RoleGuard>
  );
}

function ProductFormModal({
  initialData,
  onClose,
  onSubmit
}: {
  initialData?: InventoryItem;
  onClose: () => void;
  onSubmit: (data: InventoryItemCreate & { is_active?: boolean }) => Promise<void>;
}) {
  const [form, setForm] = useState<ProductFormState>({
    sku: initialData?.sku || "",
    name: initialData?.name || "",
    description: initialData?.description || "",
    item_type: initialData?.item_type || "RETURNABLE",
    return_required: initialData?.return_required ?? true,
    unit: initialData?.unit || "",
    unit_price: initialData?.unit_price != null ? String(initialData.unit_price) : "0",
    replacement_cost: initialData?.replacement_cost != null ? String(initialData.replacement_cost) : "",
    min_stock: initialData?.min_stock != null ? String(initialData.min_stock) : "0",
    is_active: initialData?.is_active ?? true
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid =
    form.name.trim().length > 0 &&
    numberOrNull(form.unit_price) !== null &&
    numberOrNull(form.replacement_cost) !== null &&
    integerOrNull(form.min_stock) !== null;

  function setType(type: InventoryItemType) {
    setForm((current) => ({
      ...current,
      item_type: type,
      return_required:
        type === "RETURNABLE"
          ? true
          : type === "CONSUMABLE" || type === "DISPOSABLE"
            ? false
            : current.return_required
    }));
  }

  async function submit() {
    if (!valid) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        sku: form.sku || null,
        name: form.name.trim(),
        description: form.description || null,
        item_type: form.item_type,
        return_required: form.return_required,
        unit: form.unit || null,
        unit_price: numberOrNull(form.unit_price) ?? 0,
        replacement_cost: numericPayload(form.replacement_cost),
        min_stock: integerOrNull(form.min_stock) ?? 0,
        is_active: form.is_active
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "No se pudo guardar el producto.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <ModalShell
      title={initialData ? "Editar producto" : "Crear producto"}
      description="Define los datos base del producto de inventario."
      onClose={onClose}
    >
      <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void submit(); }}>
        {error ? <ErrorState message={error} /> : null}
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            SKU
            <Input value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Nombre
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
        </div>
        <label className="grid gap-2 text-sm font-semibold">
          Descripcion
          <textarea
            className="min-h-24 rounded-md border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
          />
        </label>
        <label className="grid gap-2 text-sm font-semibold">
          Tipo de producto
          <select
            className="h-10 rounded-md border bg-white px-3 text-sm"
            value={form.item_type}
            onChange={(event) => setType(event.target.value as InventoryItemType)}
          >
            {itemTypes.map((type) => (
              <option key={type} value={type}>
                {itemTypeLabels[type]}
              </option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input
            checked={form.return_required}
            className="h-4 w-4"
            disabled={form.item_type !== "PARTIAL_CONSUMABLE"}
            type="checkbox"
            onChange={(event) => setForm({ ...form, return_required: event.target.checked })}
          />
          Requiere devolucion
        </label>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Unidad
            <Input value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Valor unitario actual
            <Input min={0} step="0.01" type="number" value={form.unit_price} onChange={(event) => setForm({ ...form, unit_price: event.target.value })} />
            <span className="text-xs font-normal text-muted-foreground">
              Este valor se usara como referencia para nuevos pedidos. Los pedidos ya creados conservaran el valor usado en su momento.
            </span>
          </label>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="grid gap-2 text-sm font-semibold">
            Costo de reposicion
            <Input min={0} step="0.01" type="number" value={form.replacement_cost} onChange={(event) => setForm({ ...form, replacement_cost: event.target.value })} />
          </label>
          <label className="grid gap-2 text-sm font-semibold">
            Stock minimo
            <Input min={0} step="1" type="number" value={form.min_stock} onChange={(event) => setForm({ ...form, min_stock: event.target.value })} />
          </label>
        </div>
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input
            checked={form.is_active}
            className="h-4 w-4"
            type="checkbox"
            onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
          />
          Producto activo
        </label>
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

function ItemTypeBadge({ type }: { type: InventoryItemType }) {
  const tone = type === "RETURNABLE" ? "success" : type === "PARTIAL_CONSUMABLE" ? "warning" : "neutral";
  return <Badge tone={tone}>{itemTypeLabels[type]}</Badge>;
}

function numberOrNull(value: string) {
  if (value === "") return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function numericPayload(value: string) {
  if (value === "") return null;
  return numberOrNull(value);
}

function integerOrNull(value: string) {
  if (value === "") return 0;
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
}

function numberValue(value: string | number | null) {
  return Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 0 });
}

function money(value: string | number | null) {
  if (value === null || value === undefined || value === "") return "-";
  return Number(value).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}
