"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Boxes, ClipboardList, PackageSearch, Warehouse } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getStockBalances } from "@/lib/api/stock";
import { getMyWarehouseAssignments } from "@/lib/api/warehouses";
import type { InventoryItemType } from "@/types/inventory";
import type { StockBalance } from "@/types/stock";
import type { MyWarehouseAssignment } from "@/types/warehouse";

const limit = 20;

const itemTypeLabels: Record<InventoryItemType, string> = {
  RETURNABLE: "Retornable",
  CONSUMABLE: "Consumible",
  PARTIAL_CONSUMABLE: "Parcial",
  DISPOSABLE: "Desechable"
};

export default function LogisticsStockPage() {
  const [stock, setStock] = useState<StockBalance[]>([]);
  const [assignments, setAssignments] = useState<MyWarehouseAssignment[]>([]);
  const [q, setQ] = useState("");
  const [warehouseId, setWarehouseId] = useState("");
  const [lowStock, setLowStock] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadSeq = useRef(0);

  const loadOptions = useCallback(async () => {
    setAssignments(await getMyWarehouseAssignments());
  }, []);

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
      setError(err instanceof Error ? err.message : "No pudimos cargar el inventario.");
    } finally {
      if (seq === loadSeq.current) setLoading(false);
    }
  }, [lowStock, page, q, warehouseId]);

  useEffect(() => {
    void loadOptions();
  }, [loadOptions]);

  useEffect(() => {
    void loadStock();
  }, [loadStock]);

  const metrics = useMemo(() => {
    const warehouseIds = new Set(stock.map((item) => item.warehouse_id));
    const totalAvailable = stock.reduce((sum, item) => sum + Number(item.available_quantity || 0), 0);
    const estimatedValue = stock.reduce((sum, item) => sum + Number(item.estimated_stock_value || 0), 0);
    return [
      { title: "Productos en mis bodegas", value: stock.length.toLocaleString("es-CL"), icon: PackageSearch },
      { title: "Bodegas asignadas con stock", value: warehouseIds.size.toLocaleString("es-CL"), icon: Warehouse },
      { title: "Productos bajo stock", value: stock.filter((item) => item.is_low_stock).length.toLocaleString("es-CL"), icon: Boxes },
      { title: "Total disponible", value: totalAvailable.toLocaleString("es-CL"), icon: Boxes },
      { title: "Valor estimado asignado", value: money(estimatedValue), icon: Boxes }
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
    <RoleGuard roles={["LOGISTICS_OPERATOR"]}>
      <div className="space-y-6">
        <PageHeader
          title="Inventario de mis bodegas"
          description="Stock visible solo para las bodegas que tienes asignadas."
          actions={
            <Link href="/logistica/stock/movimientos">
              <Button type="button">
                <ClipboardList className="h-4 w-4" />
                Movimientos
              </Button>
            </Link>
          }
        />

        {!loading && assignments.length === 0 ? (
          <EmptyState
            icon={<Warehouse className="h-6 w-6" />}
            title="No tienes bodegas asignadas"
            description="Solicita a un administrador que te asigne una bodega."
          />
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
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

            <div className="grid gap-3 rounded-lg border bg-white p-4 md:grid-cols-[240px_1fr_180px]">
              <select
                className="h-10 rounded-md border bg-white px-3 text-sm"
                value={warehouseId}
                onChange={(event) => {
                  setWarehouseId(event.target.value);
                  setPage(1);
                }}
              >
                <option value="">Todas mis bodegas</option>
                {assignments.map((assignment) => (
                  <option key={assignment.warehouse_id} value={assignment.warehouse_id}>
                    {assignment.warehouse_name}
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
              columns={columns}
              data={stock}
              emptyTitle="Sin stock registrado"
              emptyDescription="No hay stock registrado en tus bodegas asignadas."
              error={error}
              getRowKey={(item) => item.id}
              limit={limit}
              loading={loading}
              onPageChange={setPage}
              page={page}
              total={total}
            />
          </>
        )}
      </div>
    </RoleGuard>
  );
}

function quantity(value: string | number | null | undefined) {
  return Number(value || 0).toLocaleString("es-CL");
}

function money(value: string | number | null | undefined) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}
