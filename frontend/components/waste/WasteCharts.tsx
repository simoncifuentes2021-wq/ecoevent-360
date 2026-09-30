"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatKg, formatPercentage } from "@/lib/normalizers/waste";
import type { WasteChartItem } from "@/types/waste";

type ChartTooltipEntry = { payload?: WasteChartItem; value?: number | string };

function MaterialTooltip({ active, payload }: { active?: boolean; payload?: ChartTooltipEntry[] }) {
  const item = payload?.[0]?.payload;
  if (!active || !item) return null;
  return <div className="max-w-64 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
    <p className="font-semibold text-slate-900">{item.name}</p>
    <p className="mt-1 tabular-nums text-slate-700">Total: {formatKg(item.kg)}</p>
    <p className="mt-1 text-xs text-emerald-800">Desde acopios: {formatKg(item.collection_points_kg ?? 0)}</p>
    <p className="text-xs text-slate-600">Registro directo: {formatKg(item.direct_kg ?? 0)}</p>
    <p className="text-xs text-slate-500">{formatPercentage(item.percentage ?? 0)} del total</p>
  </div>;
}

function StandardTooltip({ active, payload }: { active?: boolean; payload?: ChartTooltipEntry[] }) {
  const item = payload?.[0]?.payload;
  if (!active || !item) return null;
  return <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-lg">
    <p className="font-semibold text-slate-900">{item.name}</p>
    <p className="mt-1 tabular-nums text-slate-700">{formatKg(Number(payload?.[0]?.value ?? item.kg))}</p>
    {item.percentage !== undefined ? <p className="text-xs text-slate-500">{formatPercentage(item.percentage)} del total</p> : null}
  </div>;
}

function ChartCard({ title, description, children, loading = false }: { title: string; description: string; children: React.ReactNode; loading?: boolean }) {
  return <Card className="h-full min-w-0">
    <CardHeader className="pb-3"><h3 className="text-base font-bold text-slate-950">{title}</h3><p className="mt-1 text-xs text-slate-500">{description}</p></CardHeader>
    <CardContent className="min-h-[18rem] p-3 sm:p-5">
      {loading ? <div className="h-64 animate-pulse rounded-lg bg-slate-100" aria-label={`Cargando ${title.toLowerCase()}`} /> : children}
    </CardContent>
  </Card>;
}

export function WasteCharts({ byType, bySource, byCollectionPoint, totalKg, loading = false }: {
  byType: WasteChartItem[];
  bySource: WasteChartItem[];
  byCollectionPoint: WasteChartItem[];
  totalKg: number;
  loading?: boolean;
}) {
  const types = [...byType].sort((a, b) => b.kg - a.kg).map((item) => ({ ...item, label: item.name }));
  const sources = bySource.map((item) => ({
    ...item,
    name: item.source === "COLLECTION_POINT" ? "Acopios" : item.source === "DIRECT" ? "Registro directo" : item.name,
    percentage: item.percentage ?? (totalKg > 0 ? (item.kg / totalKg) * 100 : 0)
  }));
  const points = [...byCollectionPoint]
    .sort((a, b) => b.kg - a.kg)
    .map((item) => ({ ...item, label: `${item.code ? `${item.code} · ` : ""}${item.name}` }));
  const materialHeight = Math.max(230, Math.min(440, types.length * 42 + 42));
  const pointHeight = Math.max(230, Math.min(440, points.length * 38 + 42));

  return <div className="grid min-w-0 gap-4 lg:grid-cols-2">
    <ChartCard title="Distribución por material" description="Peso total por tipo; el detalle separa Acopios y registro directo." loading={loading}>
      {types.length === 0 ? <EmptyState title="Sin materiales registrados" description="Cuando se registren residuos, aquí verás qué materiales predominan." /> : <>
        <div className="max-h-[30rem] overflow-y-auto" style={{ height: materialHeight }}>
          <ResponsiveContainer height="100%" width="100%"><BarChart data={types} layout="vertical" margin={{ left: 4, right: 18, top: 4, bottom: 4 }}>
            <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
            <XAxis axisLine={false} tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} tickFormatter={(value) => `${value} kg`} type="number" />
            <YAxis axisLine={false} dataKey="label" tick={{ fontSize: 11, fill: "#475569" }} tickFormatter={(value: string) => value.length > 21 ? `${value.slice(0, 20)}…` : value} tickLine={false} type="category" width={125} />
            <Tooltip content={<MaterialTooltip />} cursor={{ fill: "#f1f5f9" }} />
            <Bar dataKey="collection_points_kg" name="Acopios" stackId="source" fill="#047857" maxBarSize={26} />
            <Bar dataKey="direct_kg" name="Registro directo" stackId="source" fill="#94a3b8" maxBarSize={26} radius={[0, 7, 7, 0]} />
          </BarChart></ResponsiveContainer>
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-600" aria-label="Fuentes del material">
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-emerald-700" aria-hidden="true" />Acopios</span>
          <span className="inline-flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-slate-400" aria-hidden="true" />Registro directo</span>
        </div>
      </>}
    </ChartCard>

    <ChartCard title="Origen del registro" description="Peso y proporción recibidos por cada vía." loading={loading}>
      {sources.length === 0 ? <EmptyState title="Sin registros" description="El origen aparecerá cuando se registren residuos." /> : <div className="flex h-64 flex-col justify-center gap-7 px-2 sm:px-5">
        {sources.map((source, index) => {
          const isCollection = source.source === "COLLECTION_POINT";
          const color = isCollection ? "bg-emerald-700" : "bg-slate-500";
          const percentage = Math.min(100, Math.max(0, source.percentage ?? 0));
          return <div key={source.source || source.name}>
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <span className="font-semibold text-slate-900">{source.name || `Origen ${index + 1}`}</span>
              <span className="tabular-nums text-sm font-semibold text-slate-800">{formatKg(source.kg)} · {formatPercentage(percentage)}</span>
            </div>
            <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100" role="img" aria-label={`${source.name}: ${formatKg(source.kg)}, ${formatPercentage(percentage)}`}>
              <div className={`h-full rounded-full ${color}`} style={{ width: `${percentage}%` }} />
            </div>
            <p className="mt-1 text-xs text-slate-500">{source.records_count ?? 0} registros</p>
          </div>;
        })}
      </div>}
    </ChartCard>

    <div className="lg:col-span-2"><ChartCard title="Recepción por acopio" description="Peso recibido en cada punto, de mayor a menor." loading={loading}>
      {points.length === 0 ? <EmptyState title="Sin registros de acopio" description="Cuando se reciban residuos en un acopio, aparecerán aquí." /> : <div className="max-h-[30rem] overflow-y-auto" style={{ height: pointHeight }}>
        <ResponsiveContainer height="100%" width="100%"><BarChart data={points} layout="vertical" margin={{ left: 4, right: 18, top: 4, bottom: 4 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" horizontal={false} />
          <XAxis axisLine={false} tick={{ fontSize: 11, fill: "#64748b" }} tickLine={false} tickFormatter={(value) => `${value} kg`} type="number" />
          <YAxis axisLine={false} dataKey="label" tick={{ fontSize: 11, fill: "#475569" }} tickFormatter={(value: string) => value.length > 24 ? `${value.slice(0, 23)}…` : value} tickLine={false} type="category" width={150} />
          <Tooltip content={<StandardTooltip />} cursor={{ fill: "#f1f5f9" }} />
          <Bar dataKey="kg" fill="#047857" maxBarSize={24} radius={[0, 7, 7, 0]} />
        </BarChart></ResponsiveContainer>
      </div>}
    </ChartCard></div>
  </div>;
}
