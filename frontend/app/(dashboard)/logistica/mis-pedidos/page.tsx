"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ClipboardList, Eye } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { EmptyState } from "@/components/common/EmptyState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { getMyLogisticsOrders } from "@/lib/api/logistics-orders";
import type { LogisticsOrder, LogisticsOrderStatus } from "@/types/logistics-order";

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
  OBSERVED: "Observado",
  CANCELLED: "Cancelado"
};

export default function LogisticsMyOrdersPage() {
  const [orders, setOrders] = useState<LogisticsOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getMyLogisticsOrders({ limit: 100 });
      setOrders(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar tus pedidos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const columns: DataTableColumn<LogisticsOrder>[] = [
    { key: "title", header: "Pedido", cell: (order) => <span className="font-semibold">{order.title}</span> },
    { key: "event", header: "Evento", cell: (order) => order.event?.name || "-" },
    { key: "warehouse", header: "Bodega", cell: (order) => order.warehouse?.name || "-" },
    { key: "total", header: "Total estimado", cell: (order) => money(order.total_estimated_amount) },
    { key: "created_at", header: "Fecha", cell: (order) => new Date(order.created_at).toLocaleDateString("es-CL") },
    {
      key: "status",
      header: "Estado",
      cell: (order) => <Badge tone={order.status === "CANCELLED" ? "danger" : "success"}>{statusLabels[order.status]}</Badge>
    }
  ];

  return (
    <RoleGuard roles={["LOGISTICS_OPERATOR"]}>
      <div className="space-y-6">
        <PageHeader
          title="Mis pedidos logisticos"
          description="Pedidos logisticos asignados para preparacion futura. En esta etapa solo puedes verlos."
        />
        {!loading && !error && orders.length === 0 ? (
          <EmptyState
            icon={<ClipboardList className="h-6 w-6" />}
            title="Aun no tienes pedidos logisticos asignados"
            description="Cuando un supervisor te asigne un pedido aparecera aqui."
          />
        ) : (
          <DataTable
            actions={(order) => (
              <Link href={`/logistica/mis-pedidos/${order.id}`}>
                <Button size="sm" type="button" variant="secondary">
                  <Eye className="h-4 w-4" />
                </Button>
              </Link>
            )}
            columns={columns}
            data={orders}
            emptyTitle="Sin pedidos asignados"
            error={error}
            getRowKey={(order) => order.id}
            loading={loading}
          />
        )}
      </div>
    </RoleGuard>
  );
}

function money(value: string | number) {
  return Number(value || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" });
}
