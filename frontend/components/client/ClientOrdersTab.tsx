"use client";

import { useCallback, useEffect, useState } from "react";
import { PackageCheck } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { Card, CardContent } from "@/components/ui/card";
import { getEventOrders } from "@/lib/api/orders";
import type { EventOrder } from "@/types/order";
import { dateValue, numberValue, OrderStatusBadge, ProgressLine } from "@/components/orders/order-ui";

export function ClientOrdersTab({ eventId }: { eventId: string }) {
  const [orders, setOrders] = useState<EventOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getEventOrders(eventId, { page: 1, limit: 50 });
      setOrders(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar pedidos.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (orders.length === 0) return <EmptyState icon={<PackageCheck className="h-6 w-6" />} title="Sin pedidos logísticos" description="Aún no hay elementos logísticos asociados a este evento." />;

  return (
    <div className="grid gap-4">
      {orders.map((order) => (
        <Card key={order.id}>
          <CardContent className="space-y-4 p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-lg font-bold">{order.title}</p>
                <p className="text-sm text-slate-600">Fecha requerida: {dateValue(order.required_date)}</p>
              </div>
              <OrderStatusBadge status={order.status} />
            </div>
            <div className="grid gap-2 md:grid-cols-3">
              <ProgressLine label="Carga" value={order.progress.load_progress_percentage} count={`${order.progress.loaded_items}/${order.progress.total_items}`} />
              <ProgressLine label="Entrega" value={order.progress.delivery_progress_percentage} count={`${order.progress.delivered_items}/${order.progress.total_items}`} />
              <ProgressLine label="Retorno" value={order.progress.return_progress_percentage} count={`${order.progress.returned_items}/${order.progress.total_items}`} />
            </div>
            <div className="grid gap-2 md:grid-cols-2">
              {(order.items || []).map((item) => <div className="rounded-lg border bg-slate-50 p-3 text-sm" key={item.id}><span className="font-semibold">{item.item_name_snapshot}</span><span className="text-slate-600"> · {numberValue(item.quantity)} {item.unit || ""}</span></div>)}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
