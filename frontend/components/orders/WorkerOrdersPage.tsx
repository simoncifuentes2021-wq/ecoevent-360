"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, Eye } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { MobileShell } from "@/components/worker/MobileShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getMyOrders } from "@/lib/api/orders";
import type { EventOrder } from "@/types/order";
import { dateValue, OrderStatusBadge, ProgressLine } from "@/components/orders/order-ui";

export function WorkerOrdersPage() {
  const [orders, setOrders] = useState<EventOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getMyOrders({ page: 1, limit: 50 });
      setOrders(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar tus pedidos.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <MobileShell title="Mis pedidos" description="Checklist de carga, entrega y retorno asignado a ti.">
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error && orders.length === 0 ? <EmptyState icon={<ClipboardCheck className="h-6 w-6" />} title="No tienes pedidos asignados." description="Cuando te asignen un pedido logístico aparecerá aquí." /> : null}
      <div className="grid gap-3">
        {orders.map((order) => (
          <Card key={order.id}>
            <CardContent className="space-y-4 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-lg font-bold">{order.title}</p>
                  <p className="text-sm text-slate-600">{order.event?.name || "Evento"} · {order.event?.client?.business_name || "Cliente"}</p>
                </div>
                <OrderStatusBadge status={order.status} />
              </div>
              <p className="text-sm font-semibold text-slate-700">Fecha requerida: {dateValue(order.required_date)}</p>
              <div className="grid gap-2">
                <ProgressLine label="Carga" value={order.progress.load_progress_percentage} count={`${order.progress.loaded_items}/${order.progress.total_items}`} />
                <ProgressLine label="Entrega" value={order.progress.delivery_progress_percentage} count={`${order.progress.delivered_items}/${order.progress.total_items}`} />
                <ProgressLine label="Retorno" value={order.progress.return_progress_percentage} count={`${order.progress.returned_items}/${order.progress.total_items}`} />
              </div>
              <Link href={`/worker/pedidos/${order.id}`}>
                <Button className="w-full"><Eye className="h-4 w-4" />Ver checklist</Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </MobileShell>
  );
}
