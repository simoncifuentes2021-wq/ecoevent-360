import { ClipboardList, MapPinned, PackageSearch, Scale } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatKg, formatPercentage } from "@/lib/normalizers/waste";
import type { WasteSummary } from "@/types/waste";

export function WasteSummaryCards({ summary, loading = false }: { summary: WasteSummary; loading?: boolean }) {
  const mainMaterial = summary.top_waste_type;
  const cards = [
    {
      label: "Total residuos registrados",
      value: formatKg(summary.total_event_kg),
      detail: "Acopios + registros directos del evento",
      icon: Scale,
      prominent: true
    },
    {
      label: "Recibido en acopios",
      value: formatKg(summary.collection_points.weight_kg),
      detail: `${formatPercentage(summary.collection_points.percentage)} del total registrado`,
      icon: MapPinned
    },
    {
      label: "Registros realizados",
      value: summary.total_records.toLocaleString("es-CL"),
      detail: "Acopios + registros directos",
      icon: ClipboardList
    },
    {
      label: "Material principal",
      value: mainMaterial?.name || "Sin datos",
      detail: mainMaterial ? `${formatKg(mainMaterial.kg)} · ${formatPercentage(mainMaterial.percentage ?? 0)} del total` : "Se mostrará al registrar residuos",
      icon: PackageSearch
    }
  ];

  return <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
    {cards.map(({ label, value, detail, icon: Icon, prominent }) => <Card key={label} className={`h-full ${prominent ? "border-emerald-200 bg-gradient-to-br from-white to-emerald-50 shadow-md" : ""}`}>
      <CardContent className="flex min-h-32 items-start gap-3 p-4 sm:p-5">
        <div className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${prominent ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-700"}`} aria-hidden="true"><Icon className="h-5 w-5" /></div>
        <div className="min-w-0">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
          {loading ? <div className="mt-2 h-8 w-28 animate-pulse rounded bg-slate-200" aria-label={`Cargando ${label.toLowerCase()}`} /> : <p className={`mt-1 break-words font-bold tabular-nums text-slate-950 ${prominent ? "text-3xl" : "text-2xl"}`}>{value}</p>}
          <p className="mt-1 text-xs leading-5 text-slate-500">{loading ? " " : detail}</p>
        </div>
      </CardContent>
    </Card>)}
  </div>;
}
