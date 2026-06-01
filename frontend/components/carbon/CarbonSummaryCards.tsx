import { BarChart3, Cloud, Leaf, Users } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { formatKgCO2e, formatKgCO2ePerAttendee, formatTonCO2e, getMainEmissionCategory } from "@/lib/normalizers/carbon";
import type { CarbonSummary } from "@/types/carbon";

export function CarbonSummaryCards({ summary }: { summary: CarbonSummary }) {
  const cards = [
    { label: "Total kgCO2e", value: formatKgCO2e(summary.total_kg_co2e), icon: Cloud },
    { label: "Total tCO2e", value: formatTonCO2e(summary.total_ton_co2e), icon: Leaf },
    { label: "Por asistente", value: formatKgCO2ePerAttendee(summary.kg_co2e_per_attendee), icon: Users },
    { label: "Categoria principal", value: getMainEmissionCategory(summary), icon: BarChart3 }
  ];
  return <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">{cards.map((card) => { const Icon = card.icon; return <Card key={card.label}><CardContent className="flex items-center gap-4 p-4"><div className="grid h-11 w-11 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></div><div><p className="text-xs font-semibold uppercase text-slate-500">{card.label}</p><p className="mt-1 text-lg font-bold text-slate-950">{card.value}</p></div></CardContent></Card>; })}</div>;
}
