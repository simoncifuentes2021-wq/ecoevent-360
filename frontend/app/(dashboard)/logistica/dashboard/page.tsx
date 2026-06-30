"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Boxes, ClipboardList, PackageSearch, ShoppingCart, Truck, Warehouse } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getMyLogisticsOrders } from "@/lib/api/logistics-orders";
import { getStockBalances } from "@/lib/api/stock";
import { getMyWarehouseAssignments } from "@/lib/api/warehouses";
import type { LogisticsOrder } from "@/types/logistics-order";
import type { StockBalance } from "@/types/stock";
import type { MyWarehouseAssignment } from "@/types/warehouse";

export default function LogisticsDashboardPage() {
  const [assignments, setAssignments] = useState<MyWarehouseAssignment[]>([]);
  const [stock, setStock] = useState<StockBalance[]>([]);
  const [orders, setOrders] = useState<LogisticsOrder[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [assignmentResponse, stockResponse, orderResponse] = await Promise.all([
        getMyWarehouseAssignments(),
        getStockBalances({ limit: 100 }),
        getMyLogisticsOrders({ limit: 100 })
      ]);
      setAssignments(assignmentResponse);
      setStock(stockResponse.items);
      setOrders(orderResponse.items);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const metrics = useMemo(
    () => [
      { label: "Bodegas asignadas", value: assignments.length, icon: Warehouse },
      { label: "Productos disponibles", value: stock.filter((item) => Number(item.available_quantity || 0) > 0).length, icon: Boxes },
      { label: "Productos bajo stock", value: stock.filter((item) => item.is_low_stock).length, icon: PackageSearch },
      { label: "Pedidos asignados", value: orders.length, icon: ClipboardList }
    ],
    [assignments.length, orders.length, stock]
  );

  return (
    <RoleGuard roles={["LOGISTICS_OPERATOR"]}>
      <div className="space-y-6">
        <PageHeader
          title="Dashboard Operador Logistico"
          description="Vista inicial para revisar tus pedidos e inventario asignado."
        />

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => {
            const Icon = metric.icon;
            return (
              <Card key={metric.label}>
                <CardContent className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-slate-600">{metric.label}</p>
                    <p className="mt-1 text-3xl font-bold text-slate-950">{loading ? "-" : metric.value}</p>
                  </div>
                  <span className="grid h-11 w-11 place-items-center rounded-md bg-emerald-50 text-primary">
                    <Icon className="h-5 w-5" />
                  </span>
                </CardContent>
              </Card>
            );
          })}
        </section>

        <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
          <Card>
            <CardContent className="space-y-4">
              <h2 className="text-lg font-bold text-slate-950">Accesos rapidos</h2>
              <div className="grid gap-3 md:grid-cols-2">
                <Link href="/logistica/mis-pedidos">
                  <Button className="h-12 w-full">
                    <ClipboardList className="h-4 w-4" />
                    Mis pedidos
                  </Button>
                </Link>
                <Link href="/logistica/stock">
                  <Button className="h-12 w-full" variant="secondary">
                    <Boxes className="h-4 w-4" />
                    Inventario
                  </Button>
                </Link>
                <Link href="/logistica/stock/movimientos">
                  <Button className="h-12 w-full" variant="secondary">
                    <ClipboardList className="h-4 w-4" />
                    Movimientos
                  </Button>
                </Link>
                <Button className="h-12 w-full" disabled type="button" variant="secondary">
                  <ShoppingCart className="h-4 w-4" />
                  Compras - Proximamente
                </Button>
              </div>
            </CardContent>
          </Card>

          <EmptyState
            icon={<Truck className="h-6 w-6" />}
            title={orders.length ? "Pedidos logisticos activos" : "Aun no tienes pedidos logisticos asignados."}
            description={
              orders.length
                ? "Puedes revisar tus pedidos desde Mis pedidos."
                : "Cuando un supervisor asigne pedidos a tu usuario, apareceran aqui y en Mis pedidos."
            }
          />
        </section>
      </div>
    </RoleGuard>
  );
}
