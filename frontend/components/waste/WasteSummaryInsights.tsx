import { formatKg, formatPercentage } from "@/lib/normalizers/waste";
import type { WasteSummary } from "@/types/waste";

export function WasteSummaryInsights({ summary, loading = false }: { summary: WasteSummary; loading?: boolean }) {
  const topPoint = summary.top_collection_point;
  const items = [
    {
      label: "Acopio con mayor recepción",
      value: topPoint ? `${topPoint.code ? `${topPoint.code} · ` : ""}${topPoint.name}` : "Sin registros",
      detail: topPoint ? formatKg(topPoint.kg) : "Aún no hay registros de acopio"
    },
    {
      label: "Tipos de residuos registrados",
      value: summary.waste_types_count.toLocaleString("es-CL"),
      detail: "Tipos distintos entre ambas fuentes"
    },
    {
      label: "Registro directo",
      value: formatKg(summary.direct_records.weight_kg),
      detail: `${formatPercentage(summary.direct_records.percentage)} del total registrado`
    }
  ];

  return <section aria-label="Indicadores secundarios" className="grid gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 sm:grid-cols-3 sm:divide-x sm:divide-slate-200 sm:p-5">
    {items.map(({ label, value, detail }, index) => <div key={label} className={index > 0 ? "sm:pl-5" : ""}>
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
      {loading ? <div className="mt-2 h-5 w-32 animate-pulse rounded bg-slate-200" aria-label={`Cargando ${label.toLowerCase()}`} /> : <p className="mt-1 break-words text-base font-semibold text-slate-900">{value}</p>}
      <p className="mt-1 text-xs text-slate-500">{loading ? " " : detail}</p>
    </div>)}
  </section>;
}
