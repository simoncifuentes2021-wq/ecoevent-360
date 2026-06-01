import { Droplets, Flame, Zap } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import type { EnergyRecord, FuelRecord, WaterRecord } from "@/types/operations";

export function OperationalSummaryCards({ fuel, energy, water }: { fuel: FuelRecord[]; energy: EnergyRecord[]; water: WaterRecord[] }) {
  const fuelTotal = fuel.reduce((sum, item) => sum + Number(item.quantity || 0), 0);
  const energyTotal = energy.reduce((sum, item) => sum + Number(item.kwh || 0), 0);
  const waterTotal = water.reduce((sum, item) => sum + Number(item.volume_m3 || 0), 0);
  const cards = [
    { label: "Combustible", value: `${fuelTotal.toLocaleString("es-CL")} unidades`, icon: Flame },
    { label: "Energia", value: `${energyTotal.toLocaleString("es-CL")} kWh`, icon: Zap },
    { label: "Agua", value: `${waterTotal.toLocaleString("es-CL")} m3`, icon: Droplets }
  ];
  return <div className="grid gap-3 md:grid-cols-3">{cards.map((card) => { const Icon = card.icon; return <Card key={card.label}><CardContent className="flex items-center gap-3 p-4"><div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></div><div><p className="text-xs font-bold uppercase text-slate-500">{card.label}</p><p className="text-lg font-bold">{card.value}</p></div></CardContent></Card>; })}</div>;
}
