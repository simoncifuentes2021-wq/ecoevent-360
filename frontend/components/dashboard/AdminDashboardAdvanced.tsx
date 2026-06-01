"use client";

import { BarChart3, BriefcaseBusiness, Cloud, Recycle, ShieldAlert, Sparkles } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { RecentEventsTable } from "@/components/dashboard/RecentEventsTable";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { AdminDashboard } from "@/types/dashboard";

export function AdminDashboardAdvanced({ dashboard }: { dashboard: AdminDashboard }) {
  return (
    <div className="space-y-6">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard description="Clientes registrados" icon={BriefcaseBusiness} title="Clientes" value={dashboard.total_clients} />
        <KpiCard description={`${dashboard.active_events} activos`} icon={Sparkles} title="Eventos" tone="lime" value={dashboard.total_events} />
        <KpiCard description="Pendientes de resolver" icon={ShieldAlert} title="Incidencias abiertas" tone="slate" value={dashboard.open_incidents} />
        <KpiCard description={`${dashboard.completed_tasks_rate}% tareas completas`} icon={BarChart3} title="Cumplimiento" tone="blue" value={`${dashboard.completed_tasks_rate}%`} />
        <KpiCard description="Acumulado operativo" icon={Recycle} title="Residuos kg" value={dashboard.total_waste_kg.toFixed(1)} />
        <KpiCard description="Total plataforma" icon={Cloud} title="Huella tCO2e" tone="blue" value={dashboard.total_carbon_tco2e.toFixed(2)} />
      </section>
      <section className="grid gap-4 xl:grid-cols-[.9fr_1.1fr]">
        <Card>
          <CardHeader><h2 className="font-semibold">Eventos por estado</h2></CardHeader>
          <CardContent className="h-72">
            {dashboard.events_by_status.length ? <ResponsiveContainer height="100%" width="100%"><BarChart data={dashboard.events_by_status}><CartesianGrid strokeDasharray="3 3" vertical={false} /><XAxis dataKey="name" /><YAxis allowDecimals={false} /><Tooltip /><Bar dataKey="value" fill="#0f766e" radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer> : <EmptyState title="Sin datos" description="Aun no hay estados agregados." />}
          </CardContent>
        </Card>
        {dashboard.latest_events.length ? <RecentEventsTable events={dashboard.latest_events} /> : <EmptyState title="Sin eventos recientes" description="Los ultimos eventos apareceran aqui." />}
      </section>
    </div>
  );
}
