"use client";

import Link from "next/link";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ClientDashboardCards } from "@/components/client/ClientDashboardCards";
import { ClientEventCard } from "@/components/client/ClientEventCard";
import { ClientEmptyState } from "@/components/client/ClientEmptyState";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { ClientDashboard as ClientDashboardType } from "@/types/clientDashboard";

export function ClientDashboard({ dashboard }: { dashboard: ClientDashboardType }) {
  return (
    <div className="space-y-6">
      <ClientDashboardCards dashboard={dashboard} />
      <section className="grid gap-4 xl:grid-cols-[1fr_.8fr]">
        <Card>
          <CardHeader><h2 className="font-semibold">Indicadores por evento</h2></CardHeader>
          <CardContent className="h-80">
            {dashboard.indicators_by_event.length ? (
              <ResponsiveContainer height="100%" width="100%">
                <BarChart data={dashboard.indicators_by_event}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="event_name" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="waste_total_kg" fill="#0f766e" name="Residuos kg" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="carbon_tco2e" fill="#0369a1" name="tCO2e" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <ClientEmptyState title="Sin indicadores historicos" description="Los indicadores se consolidaran cuando existan eventos con datos ambientales." />}
          </CardContent>
        </Card>
        <Card>
          <CardHeader><h2 className="font-semibold">Accesos rapidos</h2></CardHeader>
          <CardContent className="grid gap-3">
            <Link href="/client/mis-eventos"><Button className="w-full" type="button">Ver mis eventos</Button></Link>
            <Link href="/client/reportes"><Button className="w-full" type="button" variant="secondary">Ver reportes</Button></Link>
            <Link href="/client/indicadores"><Button className="w-full" type="button" variant="secondary">Ver indicadores</Button></Link>
          </CardContent>
        </Card>
      </section>
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-xl font-bold text-slate-950">Ultimos eventos</h2>
          <Link href="/client/mis-eventos"><Button type="button" variant="secondary">Ver todos</Button></Link>
        </div>
        {dashboard.latest_events.length ? <div className="grid gap-4 xl:grid-cols-2">{dashboard.latest_events.map((event) => <ClientEventCard event={event} key={event.id} />)}</div> : <ClientEmptyState title="Sin eventos disponibles" description="Aun no hay eventos asociados a tu cuenta cliente." />}
      </section>
    </div>
  );
}
