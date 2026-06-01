"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { SurveySummary } from "@/types/survey";

const colors = ["#0f766e", "#65a30d", "#0369a1", "#f59e0b", "#be123c", "#475569"];

function ChartCard({ title, children, empty }: { title: string; children: React.ReactNode; empty?: boolean }) {
  return (
    <Card>
      <CardHeader><h3 className="font-semibold">{title}</h3></CardHeader>
      <CardContent className="h-72">
        {empty ? <EmptyState title="Sin datos" description="Importa respuestas para alimentar este grafico." /> : children}
      </CardContent>
    </Card>
  );
}

export function SurveyCharts({ summary }: { summary: SurveySummary }) {
  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <ChartCard empty={summary.responses_by_zone.length === 0} title="Respuestas por zona">
        <ResponsiveContainer height="100%" width="100%"><BarChart data={summary.responses_by_zone}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#0f766e" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard empty={summary.transport_modes.length === 0} title="Modos de transporte">
        <ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={summary.transport_modes} dataKey="value" innerRadius={55} outerRadius={90} nameKey="name">{summary.transport_modes.map((_, index) => <Cell fill={colors[index % colors.length]} key={index} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard empty={summary.main_problems.length === 0} title="Problemas principales">
        <ResponsiveContainer height="100%" width="100%"><BarChart data={summary.main_problems} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis dataKey="name" type="category" width={90} /><Tooltip /><Bar dataKey="value" fill="#65a30d" radius={[0, 8, 8, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
