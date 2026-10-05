import { Clock } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { EventDashboard } from "@/types/dashboard";

export function EventRecentActivity({ dashboard }: { dashboard: EventDashboard }) {
  const items = [
    ...dashboard.recommendations.map((item, index) => ({ id: `rec-${index}`, title: item, description: "Recomendacion operacional" })),
    ...dashboard.evidences.recent.map((item) => ({ id: item.id, title: item.description || "Evidencia reciente", description: item.created_at ? new Date(item.created_at).toLocaleString("es-CL", { timeZone: "America/Santiago" }) : "" }))
  ];

  return (
    <Card className="border-slate-200/80 shadow-[0_12px_32px_-24px_rgba(15,23,42,0.45)]">
      <CardHeader className="bg-slate-50/70"><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Seguimiento</p><h3 className="mt-1 text-base font-bold text-slate-950">Actividad y recomendaciones</h3></CardHeader>
      <CardContent>
        {items.length ? (
          <div className="space-y-3">
            {items.slice(0, 6).map((item) => <div className="flex gap-3 rounded-xl bg-slate-50 p-3" key={item.id}><Clock className="mt-0.5 h-4 w-4 text-slate-500" /><div><p className="text-sm font-semibold text-slate-950">{item.title}</p><p className="text-xs text-slate-500">{item.description}</p></div></div>)}
          </div>
        ) : <EmptyState title="Sin actividad reciente" description="El dashboard mostrara recomendaciones cuando existan datos suficientes." />}
      </CardContent>
    </Card>
  );
}
