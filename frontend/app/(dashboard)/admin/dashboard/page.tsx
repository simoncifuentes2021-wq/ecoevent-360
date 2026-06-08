"use client";

import { useCallback, useEffect, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { AdminDashboardAdvanced } from "@/components/dashboard/AdminDashboardAdvanced";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { getAdminDashboard } from "@/lib/api/dashboards";
import { normalizeAdminDashboard } from "@/lib/normalizers/dashboard";
import type { AdminDashboard } from "@/types/dashboard";

export default function AdminDashboardPage() {
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setDashboard(normalizeAdminDashboard(await getAdminDashboard()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el dashboard.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

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
        {!loading && error ? <ErrorState message={error} title="No se pudo cargar el dashboard" onRetry={load} /> : null}
        {!loading && dashboard ? <AdminDashboardAdvanced dashboard={dashboard} /> : null}
      </div>
    </RoleGuard>
  );
}
