"use client";

import { AlertTriangle, CheckCircle2, MapPin, PackageSearch, Plus, Search } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import type { InventoryItem } from "@/types/inventory";
import type { StockBalance } from "@/types/stock";
import type { Warehouse } from "@/types/warehouse";

type Props = {
  products: InventoryItem[];
  stock: StockBalance[];
  warehouseId: string;
  warehouses: Warehouse[];
  selectedProductIds: Set<string>;
  query: string;
  onQueryChange: (value: string) => void;
  onAdd: (product: InventoryItem) => void;
};

export function WarehouseProductCatalog({
  products,
  stock,
  warehouseId,
  warehouses,
  selectedProductIds,
  query,
  onQueryChange,
  onAdd
}: Props) {
  const warehouse = warehouses.find((item) => item.id === warehouseId);
  const balancesByProduct = new Map<string, StockBalance[]>();
  for (const balance of stock) {
    const balances = balancesByProduct.get(balance.item_id) || [];
    balances.push(balance);
    balancesByProduct.set(balance.item_id, balances);
  }

  const normalizedQuery = query.trim().toLowerCase();
  const visibleProducts = products
    .filter((product) => !selectedProductIds.has(product.id))
    .filter((product) => {
      if (!normalizedQuery) return true;
      return [product.name, product.sku, product.description, product.unit, product.item_type]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalizedQuery));
    })
    .sort((left, right) => {
      const leftAvailable = availableAt(balancesByProduct.get(left.id), warehouseId);
      const rightAvailable = availableAt(balancesByProduct.get(right.id), warehouseId);
      if ((leftAvailable > 0) !== (rightAvailable > 0)) return rightAvailable > 0 ? 1 : -1;
      return left.name.localeCompare(right.name, "es");
    });

  const productsInWarehouse = visibleProducts.filter(
    (product) => availableAt(balancesByProduct.get(product.id), warehouseId) > 0
  ).length;

  return (
    <Card>
      <CardContent className="space-y-3">
        {!warehouseId ? (
          <div className="rounded-lg border border-dashed border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            Selecciona primero la bodega de origen para cargar su disponibilidad.
          </div>
        ) : (
          <div className="flex flex-col justify-between gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 sm:flex-row sm:items-center">
            <div>
              <p className="font-semibold text-emerald-950">Productos de {warehouse?.name || "la bodega seleccionada"}</p>
              <p className="text-xs text-emerald-800">Los productos con stock aquí aparecen primero. Los demás siguen disponibles para compra o transferencia.</p>
            </div>
            <span className="whitespace-nowrap rounded-full bg-white px-3 py-1 text-xs font-bold text-emerald-800">
              {productsInWarehouse} con stock · {products.length} registrados
            </span>
          </div>
        )}

        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <Input
            className="pl-9"
            disabled={!warehouseId}
            placeholder="Buscar entre todos los productos por nombre, SKU, tipo o unidad"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
          />
        </div>

        <div className="grid max-h-[28rem] gap-2 overflow-y-auto pr-1">
          {warehouseId && visibleProducts.length === 0 ? (
            <div className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
              {products.length === selectedProductIds.size
                ? "Todos los productos del catálogo ya fueron agregados."
                : "No encontramos productos con esa búsqueda."}
            </div>
          ) : null}

          {warehouseId
            ? visibleProducts.map((product) => {
                const balances = balancesByProduct.get(product.id) || [];
                const selectedAvailable = availableAt(balances, warehouseId);
                const otherLocations = balances
                  .filter((balance) => balance.warehouse_id !== warehouseId && Number(balance.available_quantity) > 0)
                  .sort((left, right) => Number(right.available_quantity) - Number(left.available_quantity));
                const hasSelectedStock = selectedAvailable > 0;
                const hasOtherStock = otherLocations.length > 0;

                return (
                  <button
                    className="grid gap-3 rounded-lg border bg-white p-3 text-left transition hover:border-primary hover:bg-emerald-50/60 lg:grid-cols-[minmax(190px,1fr)_170px_minmax(230px,1.3fr)_36px] lg:items-center"
                    key={product.id}
                    onClick={() => onAdd(product)}
                    type="button"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold">{product.name}</p>
                      <p className="text-xs text-muted-foreground">{product.sku || "Sin SKU"} · {product.unit || "sin unidad"}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Disponible en origen</p>
                      <p className={`flex items-center gap-1.5 font-bold ${hasSelectedStock ? "text-emerald-700" : "text-amber-700"}`}>
                        {hasSelectedStock ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
                        {formatQuantity(selectedAvailable)} {product.unit || "unidades"}
                      </p>
                    </div>
                    <div className="min-w-0">
                      <p className="flex items-center gap-1 text-xs text-muted-foreground"><MapPin className="h-3.5 w-3.5" /> Otras bodegas</p>
                      <p className="text-sm font-medium text-slate-700">
                        {hasOtherStock
                          ? otherLocations.map((balance) => `${balance.warehouse_name}: ${formatQuantity(balance.available_quantity)}`).join(" · ")
                          : "Sin disponibilidad en otras bodegas"}
                      </p>
                      {!hasSelectedStock ? (
                        <p className="mt-1 text-xs font-semibold text-amber-700">
                          {hasOtherStock ? "Se podrá transferir desde otra bodega." : "El faltante podrá enviarse a compra."}
                        </p>
                      ) : null}
                    </div>
                    <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
                      {hasSelectedStock || hasOtherStock ? <Plus className="h-4 w-4" /> : <PackageSearch className="h-4 w-4" />}
                    </span>
                  </button>
                );
              })
            : null}
        </div>
      </CardContent>
    </Card>
  );
}

function availableAt(balances: StockBalance[] | undefined, warehouseId: string) {
  return Number(balances?.find((balance) => balance.warehouse_id === warehouseId)?.available_quantity || 0);
}

function formatQuantity(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 2 });
}
