"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ClientDashboardCards } from "@/components/client/ClientDashboardCards";
import { ClientEmptyState } from "@/components/client/ClientEmptyState";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { ClientDashboard } from "@/types/clientDashboard";

export function ClientIndicatorsPage({ dashboard }: { dashboard: ClientDashboard }) {
  const data = dashboard.indicators_by_event;
  return (
    <div className="space-y-6">
      <ClientDashboardCards dashboard={dashboard} />
      <div className="grid gap-4 xl:grid-cols-2">
        <Chart title="Residuos por evento" data={data} dataKey="waste_total_kg" />
        <Chart title="Huella por evento" data={data} dataKey="carbon_tco2e" />
        <Chart title="Satisfaccion por evento" data={data} dataKey="average_rating" />
        <Chart title="Cumplimiento operativo" data={data} dataKey="tasks_completion_rate" />
      </div>
    </div>
  );
}

function Chart({ title, data, dataKey }: { title: string; data: ClientDashboard["indicators_by_event"]; dataKey: string }) {
  return (
    <Card>
      <CardHeader><h2 className="font-semibold">{title}</h2></CardHeader>
      <CardContent className="h-72">
        {data.length ? <ResponsiveContainer height="100%" width="100%"><BarChart data={data}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="event_name" tick={{ fontSize: 11 }} /><YAxis /><Tooltip /><Bar dataKey={dataKey} fill="#0f766e" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer> : <ClientEmptyState title="Sin datos" description="Aun no hay informacion suficiente para graficar." />}
      </CardContent>
    </Card>
  );
}
