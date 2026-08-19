"use client";

import { CheckCircle2, Database, Fuel, Gauge, Leaf, Zap } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent } from "@/components/ui/card";

type OfficialImpact = {
  actions_count: number;
  metrics: Record<string, string | null>;
  actions: Array<{ id: string; name: string; session_name: string; methodology?: string | null; approved_at?: string | null; approved_by?: string | null; metrics: Record<string, string> }>;
  breakdown: Array<{ session_id?: string | null; session_name: string; actions_count: number; metrics: Record<string, string> }>;
  methodologies: Array<{ id: string; name?: string; baseline_technology?: string; actual_technology?: string; description?: string }>;
  sources: Array<{ id: string; technology?: string; factor_value?: string; factor_unit?: string; source?: string; year?: number }>;
  equivalences: Array<{ name: string; value: string; unit: string; source: string; year: number }>;
  disclaimer: string;
};

const number = (value: string | null | undefined, digits = 3) => value == null ? "No calculado" : new Intl.NumberFormat("es-CL", { maximumFractionDigits: digits }).format(Number(value));

export function ClientEnvironmentalImpactTab({ data }: { data?: unknown }) {
  const impact = data as OfficialImpact | undefined;
  if (!impact?.actions_count) return <EmptyState title="Sin resultados ambientales aprobados" description="Los resultados aparecerán aquí después de que un administrador valide formalmente el cálculo." />;
  const cards = [
    ["CO₂e evitado", impact.metrics.CO2E_AVOIDED_KG, "kg", Leaf],
    ["Energía utilizada", impact.metrics.ENERGY_KWH, "kWh", Zap],
    ["Combustible evitado", impact.metrics.FUEL_AVOIDED_L, "L", Fuel],
    ["PM2.5 evitado", impact.metrics.PM25_AVOIDED_KG, "kg", Gauge],
    ["PM10 evitado", impact.metrics.PM10_AVOIDED_KG, "kg", Gauge],
    ["NOx evitado", impact.metrics.NOX_AVOIDED_KG, "kg", Gauge],
  ] as const;
  return <div className="space-y-5">
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4"><div className="flex items-center gap-2 font-bold text-emerald-900"><CheckCircle2 className="h-5 w-5" />Resultados oficialmente aprobados</div><p className="mt-1 text-sm text-emerald-800">Solo se muestran acciones revisadas y aprobadas. Impacto evitado y Huella de Carbono son indicadores independientes.</p></div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{cards.map(([label, value, unit, Icon]) => <Card key={label}><CardContent><Icon className="h-5 w-5 text-emerald-700" /><p className="mt-3 text-sm text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold">{number(value)} {value == null ? "" : unit}</p></CardContent></Card>)}</div>
    <section><h3 className="mb-3 text-lg font-bold">Resultados por alcance</h3><div className="grid gap-3 lg:grid-cols-2">{impact.breakdown.map((scope) => <article className="rounded-2xl border bg-white p-4" key={scope.session_id || "EVENT"}><div className="flex items-center justify-between"><h4 className="font-bold">{scope.session_name}</h4><span className="rounded-full bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800">{scope.actions_count} aprobadas</span></div><div className="mt-3 grid grid-cols-2 gap-2 text-sm"><Metric label="CO₂e evitado" value={`${number(scope.metrics.CO2E_AVOIDED_KG)} kg`} /><Metric label="Energía" value={`${number(scope.metrics.ENERGY_KWH)} kWh`} /><Metric label="Combustible" value={`${number(scope.metrics.FUEL_AVOIDED_L)} L`} /><Metric label="NOx evitado" value={`${number(scope.metrics.NOX_AVOIDED_KG)} kg`} /></div></article>)}</div></section>
    <section><h3 className="mb-3 text-lg font-bold">Acciones incluidas</h3><div className="overflow-x-auto rounded-2xl border bg-white"><table className="w-full min-w-[760px] text-sm"><thead className="bg-slate-50 text-left"><tr>{["Acción", "Alcance", "Metodología", "CO₂e evitado", "Aprobación"].map((label) => <th className="p-3" key={label}>{label}</th>)}</tr></thead><tbody>{impact.actions.map((action) => <tr className="border-t" key={action.id}><td className="p-3 font-semibold">{action.name}</td><td className="p-3">{action.session_name}</td><td className="p-3">{action.methodology || "—"}</td><td className="p-3">{number(action.metrics.CO2E_AVOIDED_KG)} kg</td><td className="p-3"><p>{action.approved_by || "Administrador"}</p><p className="text-xs text-slate-500">{action.approved_at ? new Date(action.approved_at).toLocaleDateString("es-CL") : "—"}</p></td></tr>)}</tbody></table></div></section>
    <section><h3 className="mb-3 flex items-center gap-2 text-lg font-bold"><Database className="h-5 w-5 text-emerald-700" />Metodologías y fuentes</h3><div className="grid gap-3 lg:grid-cols-2">{impact.methodologies.map((method) => <article className="rounded-2xl border bg-white p-4" key={method.id}><p className="font-bold">{method.name}</p><p className="mt-2 text-sm text-slate-600">Línea base: {method.baseline_technology}</p><p className="text-sm text-slate-600">Escenario real: {method.actual_technology}</p><p className="mt-2 text-sm">{method.description}</p></article>)}{impact.sources.map((source) => <article className="rounded-2xl border bg-white p-4" key={source.id}><p className="font-bold">{source.technology}</p><p className="mt-1 font-mono text-sm text-emerald-800">{number(source.factor_value, 10)} {source.factor_unit}</p><p className="mt-2 text-xs text-slate-500">{source.source} · {source.year}</p></article>)}</div></section>
    {impact.equivalences.length ? <section><h3 className="mb-3 text-lg font-bold">Equivalencias comunicacionales</h3><div className="grid gap-3 md:grid-cols-2">{impact.equivalences.map((item) => <article className="rounded-2xl border bg-white p-4" key={`${item.name}-${item.year}`}><p className="text-sm text-slate-500">{item.name}</p><p className="mt-1 text-xl font-bold text-emerald-800">{number(item.value)} {item.unit.replace(/\/kgCO2e$/, "")}</p><p className="mt-2 text-xs text-slate-500">{item.source} · {item.year}</p></article>)}</div></section> : null}
    <p className="rounded-xl bg-amber-50 p-3 text-xs text-amber-800">{impact.disclaimer}</p>
  </div>;
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{label}</p><p className="mt-1 font-bold">{value}</p></div>; }
