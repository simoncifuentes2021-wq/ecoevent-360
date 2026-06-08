"use client";

import { useEffect, useState } from "react";

import { ClientDashboard } from "@/components/client/ClientDashboard";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { useAuth } from "@/hooks/useAuth";
import { getClientDashboard } from "@/lib/api/clientDashboard";
import type { ClientDashboard as ClientDashboardType } from "@/types/clientDashboard";

export default function ClientDashboardPage() {
  const { user } = useAuth();
  const [dashboard, setDashboard] = useState<ClientDashboardType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        setDashboard(await getClientDashboard());
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar los indicadores.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  return (
    <RoleGuard roles={["CLIENT"]}>
      <div className="space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase text-primary">Portal cliente</p>
          <h1 className="mt-1 text-3xl font-bold">Hola, {user?.full_name || "cliente"}</h1>
          <p className="mt-2 text-muted-foreground">Vista ejecutiva de tus eventos, indicadores ambientales, encuestas y reportes.</p>
        </div>
        {loading ? <LoadingState label="Cargando dashboard cliente..." /> : null}
        {!loading && error ? <ErrorState message={error} title="No se pudo cargar el dashboard" /> : null}
        {!loading && dashboard ? <ClientDashboard dashboard={dashboard} /> : null}
      </div>
    </RoleGuard>
  );
}
