"use client";

import { useCallback, useEffect, useState } from "react";
import { ClipboardCheck, PackageCheck, Truck } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { LogisticsOrdersOverview } from "@/components/logistics/LogisticsOrdersOverview";
import { getMyLogisticsOrders } from "@/lib/api/logistics-orders";
import type { LogisticsOrder } from "@/types/logistics-order";

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

  return (
    <RoleGuard roles={["LOGISTICS_OPERATOR"]}>
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operación logística"
          title="Mis pedidos logisticos"
          description="Tu bandeja de trabajo para preparar, despachar, entregar y cerrar cada pedido."
        />

        <div className="grid gap-3 rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-white p-4 sm:grid-cols-3">
          <GuideStep icon={ClipboardCheck} number="1" title="Revisa" text="Confirma productos y stock." />
          <GuideStep icon={PackageCheck} number="2" title="Prepara" text="Registra carga y evidencias." />
          <GuideStep icon={Truck} number="3" title="Entrega" text="Informa resultados y cierre." />
        </div>

        <LogisticsOrdersOverview
          orders={orders}
          loading={loading}
          error={error}
          onRetry={load}
          hrefFor={(order) => `/logistica/mis-pedidos/${order.id}`}
          emptyTitle="Aún no tienes pedidos logísticos asignados"
          emptyDescription="Cuando un supervisor te asigne un pedido aparecerá aquí."
          showOperator={false}
        />
      </div>
    </RoleGuard>
  );
}

function GuideStep({ icon: Icon, number, title, text }: { icon: typeof Truck; number: string; title: string; text: string }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-white/80 p-3 shadow-sm">
      <span className="relative grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-100 text-emerald-700">
        <Icon className="h-5 w-5" />
        <span className="absolute -right-1 -top-1 grid h-4 w-4 place-items-center rounded-full bg-emerald-700 text-[9px] font-bold text-white">{number}</span>
      </span>
      <div><p className="text-sm font-bold text-slate-900">{title}</p><p className="text-xs text-slate-500">{text}</p></div>
    </div>
  );
}
