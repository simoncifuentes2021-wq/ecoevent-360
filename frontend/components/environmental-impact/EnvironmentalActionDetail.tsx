"use client";

import { CalendarDays, Database, Fuel, Gauge, Leaf, Route, Zap } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import type { EnvironmentalAction, EnvironmentalMetric, EnvironmentalMetricKey } from "@/types/environmental";

const metricLabels: Partial<Record<EnvironmentalMetricKey, string>> = {
  CO2E_BASELINE_KG: "Línea base", CO2E_ACTUAL_KG: "Escenario real", CO2E_AVOIDED_KG: "Evitado",
  PM25_BASELINE_KG: "Línea base", PM25_ACTUAL_KG: "Escenario real", PM25_AVOIDED_KG: "Evitado",
  PM10_BASELINE_KG: "Línea base", PM10_ACTUAL_KG: "Escenario real", PM10_AVOIDED_KG: "Evitado",
  NOX_BASELINE_KG: "Línea base", NOX_ACTUAL_KG: "Escenario real", NOX_AVOIDED_KG: "Evitado",
};
const groups: Array<{ title: string; icon: typeof Leaf; keys: EnvironmentalMetricKey[] }> = [
  { title: "CO₂e", icon: Leaf, keys: ["CO2E_BASELINE_KG", "CO2E_ACTUAL_KG", "CO2E_AVOIDED_KG"] },
  { title: "PM2.5", icon: Gauge, keys: ["PM25_BASELINE_KG", "PM25_ACTUAL_KG", "PM25_AVOIDED_KG"] },
  { title: "PM10", icon: Gauge, keys: ["PM10_BASELINE_KG", "PM10_ACTUAL_KG", "PM10_AVOIDED_KG"] },
  { title: "NOx", icon: Gauge, keys: ["NOX_BASELINE_KG", "NOX_ACTUAL_KG", "NOX_AVOIDED_KG"] },
];
const number = (value: string | null, digits = 6) => value === null ? "No calculado" : new Intl.NumberFormat("es-CL", { maximumFractionDigits: digits }).format(Number(value));
type SnapshotFactor = { id: string; technology: string; factor_value: string; factor_unit: string; source: string; year: number; methodology: string };
type SnapshotMethodology = { name?: string; baseline_technology?: string; actual_technology?: string; description?: string };

function snapshot(metric?: EnvironmentalMetric) {
  return (metric?.calculation_snapshot || {}) as { factors?: SnapshotFactor[]; methodology?: SnapshotMethodology };
}

export function EnvironmentalActionDetail({ action, showName, onClose }: { action: EnvironmentalAction; showName?: string; onClose: () => void }) {
  const byKey = new Map(action.metrics.map((metric) => [metric.metric_key, metric]));
  const calculated = action.metrics.find((metric) => metric.metric_key.endsWith("_AVOIDED_KG")) || action.metrics[0];
  const methodology = snapshot(calculated).methodology;
  const factors = Array.from(new Map(action.metrics.flatMap((metric) => snapshot(metric).factors || []).map((factor) => [factor.id, factor])).values());
  const energy = byKey.get("ENERGY_KWH"); const fuel = byKey.get("FUEL_AVOIDED_L");
  const isTower = action.action_type === "ELECTRIC_LIGHTING_TOWER";
  const perUnitHour = isTower && action.energy_input_mode === "PER_UNIT_HOUR" && action.energy_per_unit_hour_kwh != null && action.hours_used != null;
  const historicalTowerTotal = isTower && action.energy_input_mode === "TOTAL_MEASURED";
  return <ModalShell title={action.name} description={`${showName || "Evento completo"} · Detalle trazable del cálculo`} onClose={onClose} size="lg">
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Info icon={Zap} label="Energía generada" value={`${number(energy?.value ?? action.energy_kwh ?? null)} kWh`} />
        <Info icon={Fuel} label="Diésel evitado" value={fuel?.value == null ? "No calculado" : `${number(fuel.value)} L`} />
        <Info icon={Route} label="Distancia" value={action.distance_km == null ? "No aplica" : `${number(action.distance_km)} km`} />
        <Info icon={CalendarDays} label="Último cálculo" value={calculated ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(calculated.calculated_at)) : "Pendiente"} />
      </div>
      <section><h3 className="mb-3 text-base font-bold uppercase">Datos operacionales</h3><div className="grid gap-3 sm:grid-cols-3"><Info icon={Gauge} label={isTower ? "Cantidad de torres" : "Cantidad"} value={number(action.quantity_used)} /><Info icon={CalendarDays} label="Horas de funcionamiento" value={action.hours_used == null ? "No aplica" : `${number(action.hours_used)} h`} /><Info icon={Zap} label={isTower ? "Energía por torre/hora" : "Energía unitaria por hora"} value={perUnitHour ? `${number(action.energy_per_unit_hour_kwh ?? null)} kWh` : historicalTowerTotal ? "Registro histórico total" : "No aplica"} /></div></section>
      {perUnitHour ? <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><h3 className="font-bold uppercase">Cálculo energético</h3><p className="mt-2">{number(action.energy_per_unit_hour_kwh ?? null)} kWh × {number(action.quantity_used)} torres × {number(action.hours_used ?? null)} h = {number(action.energy_kwh ?? null)} kWh</p><p className="mt-2 text-lg font-bold text-emerald-800">Energía generada: {number(energy?.value ?? action.energy_kwh ?? null)} kWh</p></section> : null}
      <section><h3 className="mb-3 text-base font-bold">Comparación ambiental</h3><div className="grid gap-3 md:grid-cols-2">{groups.map(({ title, icon: Icon, keys }) => <article className="rounded-2xl border border-slate-200 p-4" key={title}><div className="mb-3 flex items-center gap-2"><Icon className="h-5 w-5 text-emerald-700" /><h4 className="font-bold">{title}</h4></div><div className="grid grid-cols-3 gap-2">{keys.map((key) => { const metric = byKey.get(key); const avoided = key.includes("AVOIDED"); return <div className={`rounded-xl p-3 ${avoided ? "bg-emerald-50" : "bg-slate-50"}`} key={key}><p className="text-xs text-slate-500">{metricLabels[key]}</p><p className={`mt-1 font-bold ${avoided ? "text-emerald-800" : "text-slate-800"}`}>{metric ? `${number(metric.value)} ${metric.unit}` : "—"}</p></div>; })}</div></article>)}</div></section>
      {methodology ? <section className="rounded-2xl border border-emerald-100 bg-emerald-50/50 p-5"><h3 className="font-bold">{methodology.name || "Metodología aplicada"}</h3><div className="mt-3 grid gap-3 sm:grid-cols-2"><div><p className="text-xs font-semibold uppercase text-slate-500">Línea base</p><p>{methodology.baseline_technology}</p></div><div><p className="text-xs font-semibold uppercase text-slate-500">Escenario real</p><p>{methodology.actual_technology}</p></div></div><p className="mt-3 text-sm text-slate-600">{methodology.description}</p></section> : null}
      {calculated ? <section><h3 className="mb-2 font-bold">Fórmula aplicada</h3><code className="block overflow-x-auto rounded-xl bg-slate-950 p-4 text-xs text-emerald-200">{calculated.calculation_method}</code>{calculated.is_manual_override ? <p className="mt-2 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Resultado reemplazado manualmente: {calculated.override_reason}</p> : null}</section> : null}
      <section><h3 className="mb-3 flex items-center gap-2 font-bold"><Database className="h-5 w-5 text-emerald-700" />Factores congelados en el cálculo</h3>{factors.length ? <div className="grid gap-3 md:grid-cols-2">{factors.map((factor) => <article className="rounded-xl border p-4" key={factor.id}><p className="font-semibold">{factor.technology}</p><p className="mt-1 font-mono text-sm text-emerald-800">{number(factor.factor_value, 10)} {factor.factor_unit}</p><p className="mt-2 text-xs text-slate-500">{factor.source} · {factor.year}</p><p className="mt-2 text-xs text-slate-600">{factor.methodology}</p></article>)}</div> : <p className="text-sm text-slate-500">Esta métrica no utiliza factores externos.</p>}</section>
    </div>
  </ModalShell>;
}

function Info({ icon: Icon, label, value }: { icon: typeof Leaf; label: string; value: string }) { return <div className="rounded-2xl border bg-white p-4"><Icon className="h-5 w-5 text-emerald-700" /><p className="mt-2 text-xs text-slate-500">{label}</p><p className="mt-1 font-bold">{value}</p></div>; }
