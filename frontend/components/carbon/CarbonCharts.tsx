"use client";

import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { CarbonChartItem } from "@/types/carbon";

const colors = ["#047857", "#0f766e", "#65a30d", "#0891b2", "#ca8a04", "#64748b"];

function ChartCard({ title, empty, children }: { title: string; empty: boolean; children: React.ReactNode }) {
  return <Card><CardHeader><h3 className="text-base font-bold text-slate-950">{title}</h3></CardHeader><CardContent className="h-72">{empty ? <EmptyState title="Sin datos" description="Aun no hay informacion suficiente para graficar." /> : children}</CardContent></Card>;
}

export function CarbonCharts({ byCategory, byScope, bySource, byDate }: { byCategory: CarbonChartItem[]; byScope: CarbonChartItem[]; bySource: CarbonChartItem[]; byDate: CarbonChartItem[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartCard title="Emisiones por categoria" empty={byCategory.length === 0}><ResponsiveContainer height="100%" width="100%"><BarChart data={byCategory}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip formatter={(value) => [`${value} kgCO2e`, "Emisiones"]} /><Bar dataKey="kg" fill="#047857" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer></ChartCard>
      <ChartCard title="Emisiones por alcance" empty={byScope.length === 0}><ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={byScope} dataKey="kg" innerRadius={55} outerRadius={90}>{byScope.map((_, index) => <Cell fill={colors[index % colors.length]} key={index} />)}</Pie><Tooltip formatter={(value) => [`${value} kgCO2e`, "Emisiones"]} /></PieChart></ResponsiveContainer></ChartCard>
      <ChartCard title="Emisiones por fuente" empty={bySource.length === 0}><ResponsiveContainer height="100%" width="100%"><BarChart data={bySource} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis dataKey="name" type="category" width={100} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => [`${value} kgCO2e`, "Emisiones"]} /><Bar dataKey="kg" fill="#65a30d" radius={[0, 8, 8, 0]} /></BarChart></ResponsiveContainer></ChartCard>
      <ChartCard title="Evolucion temporal" empty={byDate.length < 2}><ResponsiveContainer height="100%" width="100%"><LineChart data={byDate}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip formatter={(value) => [`${value} kgCO2e`, "Emisiones"]} /><Line dataKey="kg" stroke="#047857" strokeWidth={3} /></LineChart></ResponsiveContainer></ChartCard>
    </div>
  );
}
