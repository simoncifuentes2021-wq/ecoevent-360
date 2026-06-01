"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { WasteChartItem } from "@/types/waste";

const colors = ["#047857", "#0f766e", "#65a30d", "#0891b2", "#ca8a04", "#64748b"];

function ChartCard({ title, children, empty }: { title: string; children: React.ReactNode; empty: boolean }) {
  return <Card><CardHeader><h3 className="text-base font-bold text-slate-950">{title}</h3></CardHeader><CardContent className="h-72">{empty ? <EmptyState title="Sin datos" description="Aun no hay informacion suficiente para graficar." /> : children}</CardContent></Card>;
}

export function WasteCharts({ byType, byDestination, byZone }: { byType: WasteChartItem[]; byDestination: WasteChartItem[]; byZone: WasteChartItem[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <ChartCard title="Kg por tipo" empty={byType.length === 0}>
        <ResponsiveContainer height="100%" width="100%"><BarChart data={byType}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip formatter={(value) => [`${value} kg`, "Peso"]} /><Bar dataKey="kg" fill="#047857" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Destino" empty={byDestination.length === 0}>
        <ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={byDestination} dataKey="kg" innerRadius={55} outerRadius={90} paddingAngle={2}>{byDestination.map((_, index) => <Cell fill={colors[index % colors.length]} key={index} />)}</Pie><Tooltip formatter={(value) => [`${value} kg`, "Peso"]} /></PieChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard title="Kg por zona" empty={byZone.length === 0}>
        <ResponsiveContainer height="100%" width="100%"><BarChart data={byZone} layout="vertical"><CartesianGrid strokeDasharray="3 3" /><XAxis type="number" /><YAxis dataKey="name" type="category" width={90} tick={{ fontSize: 11 }} /><Tooltip formatter={(value) => [`${value} kg`, "Peso"]} /><Bar dataKey="kg" fill="#65a30d" radius={[0, 8, 8, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
