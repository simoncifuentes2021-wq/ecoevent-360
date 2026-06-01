"use client";

import { useEffect, useMemo, useState } from "react";
import { BarChart3, BriefcaseBusiness, Sparkles, Users } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from "recharts";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { AdminDashboardAdvanced } from "@/components/dashboard/AdminDashboardAdvanced";
import { KpiCard } from "@/components/dashboard/KpiCard";
import { QuickActions } from "@/components/dashboard/QuickActions";
import { RecentEventsTable } from "@/components/dashboard/RecentEventsTable";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { getAdminDashboard } from "@/lib/api/dashboards";
import { normalizeAdminDashboard } from "@/lib/normalizers/dashboard";
import type { Client } from "@/types/client";
import type { ListResponse } from "@/types/common";
import type { AdminDashboard } from "@/types/dashboard";
import type { Event } from "@/types/event";
import type { User } from "@/types/user";

const chartData = [
  { mes: "Ene", eventos: 8 },
  { mes: "Feb", eventos: 12 },
  { mes: "Mar", eventos: 10 },
  { mes: "Abr", eventos: 16 },
  { mes: "May", eventos: 14 },
  { mes: "Jun", eventos: 20 }
];

type DashboardData = {
  clients: ListResponse<Client> | null;
  users: ListResponse<User> | null;
  events: ListResponse<Event> | null;
  advanced: AdminDashboard | null;
};

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardData>({ clients: null, users: null, events: null, advanced: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      const advanced = await getAdminDashboard().then(normalizeAdminDashboard).catch(() => null);
      const [clients, users, events] = await Promise.allSettled([
        api.get<ListResponse<Client>>("/clients?page=1&limit=5"),
        api.get<ListResponse<User>>("/users?page=1&limit=5"),
        api.get<ListResponse<Event>>("/events?page=1&limit=5")
      ]);

      setData({
        clients: clients.status === "fulfilled" ? clients.value : null,
        users: users.status === "fulfilled" ? users.value : null,
        events: events.status === "fulfilled" ? events.value : null,
        advanced
      });

      const rejected = [clients, users, events].find((item) => item.status === "rejected");
      if (rejected?.status === "rejected") {
        setError(rejected.reason instanceof ApiError ? rejected.reason.detail : "Algunos datos no estan disponibles.");
      }
      setLoading(false);
    }
    void load();
  }, []);

  const activeEvents = useMemo(
    () => data.events?.items.filter((event) => ["PLANNING", "IN_PROGRESS"].includes(event.status)).length ?? 0,
    [data.events]
  );

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <section className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm font-semibold uppercase text-primary">Administracion</p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight">Dashboard operativo</h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Vista ejecutiva para monitorear clientes, eventos, operacion, residuos, huella y experiencia.
            </p>
          </div>
        </section>

        {loading ? <LoadingState /> : null}
        {!loading && error ? <ErrorState message={error} title="Datos parciales" /> : null}

        {!loading ? (
          <>
            {data.advanced ? (
              <AdminDashboardAdvanced dashboard={data.advanced} />
            ) : (
              <>
                <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <KpiCard description="Clientes registrados" icon={BriefcaseBusiness} title="Total clientes" value={data.clients?.total ?? 0} />
                  <KpiCard description="Usuarios del sistema" icon={Users} title="Total usuarios" tone="blue" value={data.users?.total ?? 0} />
                  <KpiCard description="Eventos creados" icon={Sparkles} title="Total eventos" tone="lime" value={data.events?.total ?? 0} />
                  <KpiCard description="Planificacion o ejecucion" icon={BarChart3} title="Eventos activos" tone="slate" value={activeEvents} />
                </section>

                <section className="grid gap-4 xl:grid-cols-[.9fr_1.1fr]">
                  <QuickActions />
                  <Card>
                    <CardHeader>
                      <h2 className="font-semibold">Tendencia de eventos</h2>
                    </CardHeader>
                    <CardContent className="h-72">
                      <ResponsiveContainer height="100%" width="100%">
                        <AreaChart data={chartData}>
                          <defs>
                            <linearGradient id="eventos" x1="0" x2="0" y1="0" y2="1">
                              <stop offset="5%" stopColor="#0f766e" stopOpacity={0.35} />
                              <stop offset="95%" stopColor="#0f766e" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} />
                          <XAxis dataKey="mes" tickLine={false} />
                          <Tooltip />
                          <Area dataKey="eventos" fill="url(#eventos)" stroke="#0f766e" strokeWidth={2} type="monotone" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </section>
              </>
            )}

            {data.events ? (
              <RecentEventsTable events={data.events.items} />
            ) : (
              <EmptyState description="El endpoint de eventos no respondio. El resto del panel permanece disponible." title="Eventos no disponibles" />
            )}
          </>
        ) : null}
      </div>
    </RoleGuard>
  );
}
