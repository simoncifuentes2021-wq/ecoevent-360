"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { DashboardBucket } from "@/types/dashboard";

const colors = ["#0f766e", "#65a30d", "#0369a1", "#f59e0b", "#be123c", "#475569"];

function ChartCard({ title, data, children }: { title: string; data: DashboardBucket[]; children: React.ReactNode }) {
  return (
    <Card className="overflow-hidden border-slate-200/80 shadow-[0_12px_32px_-24px_rgba(15,23,42,0.45)]">
      <CardHeader className="bg-slate-50/70"><p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Operación</p><h3 className="mt-1 text-base font-bold text-slate-950">{title}</h3></CardHeader>
      <CardContent className="h-80 p-5">{data.length ? children : <EmptyState title="Sin datos" description="Aún no hay información para este indicador." />}</CardContent>
    </Card>
  );
}

export function EventOperationalCharts({ tasksByStatus, incidentsByStatus }: { tasksByStatus: DashboardBucket[]; incidentsByStatus: DashboardBucket[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <ChartCard data={tasksByStatus} title="Tareas por estado">
        <ResponsiveContainer height="100%" width="100%"><BarChart data={tasksByStatus}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#0f766e" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
      </ChartCard>
      <ChartCard data={incidentsByStatus} title="Incidencias por estado">
        <ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={incidentsByStatus} dataKey="value" innerRadius={55} outerRadius={90} nameKey="name">{incidentsByStatus.map((_, index) => <Cell fill={colors[index % colors.length]} key={index} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
