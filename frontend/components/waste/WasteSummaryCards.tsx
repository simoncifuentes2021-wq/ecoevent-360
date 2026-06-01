import { Leaf, Recycle, Scale, Trash2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatKg, formatPercentage } from "@/lib/normalizers/waste";
import type { WasteSummary } from "@/types/waste";

export function WasteSummaryCards({ summary }: { summary: WasteSummary }) {
  const cards = [
    { label: "Total residuos", value: formatKg(summary.total_kg), icon: Scale },
    { label: "Recuperado", value: formatKg(summary.recovered_kg), icon: Recycle },
    { label: "Relleno sanitario", value: formatKg(summary.landfill_kg), icon: Trash2 },
    { label: "Tasa recuperacion", value: formatPercentage(summary.recovery_rate), icon: Leaf },
    ...(summary.organic_kg ? [{ label: "Organico", value: formatKg(summary.organic_kg), icon: Leaf }] : []),
    ...(summary.recycled_kg ? [{ label: "Reciclado", value: formatKg(summary.recycled_kg), icon: Recycle }] : [])
  ];

  return <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{cards.map((card) => {
    const Icon = card.icon;
    return <Card key={card.label}><CardContent className="flex items-center gap-4 p-4"><div className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase text-slate-500">{card.label}</p><p className="mt-1 text-xl font-bold text-slate-950">{card.value}</p></div></CardContent></Card>;
  })}</div>;
}
