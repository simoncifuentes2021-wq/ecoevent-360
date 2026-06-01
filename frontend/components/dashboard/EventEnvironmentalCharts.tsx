"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { DashboardBucket } from "@/types/dashboard";

const colors = ["#0f766e", "#65a30d", "#0369a1", "#f59e0b", "#be123c", "#475569"];

export function EventEnvironmentalCharts({ wasteByDestination, carbonByCategory }: { wasteByDestination: DashboardBucket[]; carbonByCategory: DashboardBucket[] }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader><h3 className="font-semibold">Residuos por destino</h3></CardHeader>
        <CardContent className="h-72">
          {wasteByDestination.length ? <ResponsiveContainer height="100%" width="100%"><PieChart><Pie data={wasteByDestination} dataKey="value" innerRadius={55} outerRadius={90} nameKey="name">{wasteByDestination.map((_, index) => <Cell fill={colors[index % colors.length]} key={index} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer> : <EmptyState title="Sin residuos" description="Registra residuos para ver este grafico." />}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><h3 className="font-semibold">Huella por categoria</h3></CardHeader>
        <CardContent className="h-72">
          {carbonByCategory.length ? <ResponsiveContainer height="100%" width="100%"><BarChart data={carbonByCategory} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false} /><XAxis type="number" /><YAxis dataKey="name" type="category" width={100} /><Tooltip /><Bar dataKey="value" fill="#0369a1" radius={[0, 8, 8, 0]} /></BarChart></ResponsiveContainer> : <EmptyState title="Sin huella" description="Agrega registros de carbono para alimentar este grafico." />}
        </CardContent>
      </Card>
    </div>
  );
}
