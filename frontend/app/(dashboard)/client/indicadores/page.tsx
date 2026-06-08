"use client";

import { useEffect, useState } from "react";

import { ClientIndicatorsPage } from "@/components/client/ClientIndicatorsPage";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { getClientDashboard } from "@/lib/api/clientDashboard";
import type { ClientDashboard } from "@/types/clientDashboard";

export default function ClientIndicatorsRoute() {
  const [dashboard, setDashboard] = useState<ClientDashboard | null>(null);
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
          <h1 className="mt-1 text-3xl font-bold">Indicadores</h1>
          <p className="mt-2 text-muted-foreground">Consolidado historico de residuos, huella, satisfaccion e indicadores operativos.</p>
        </div>
        {loading ? <LoadingState label="Cargando indicadores..." /> : null}
        {!loading && error ? <ErrorState message={error} /> : null}
        {!loading && dashboard ? <ClientIndicatorsPage dashboard={dashboard} /> : null}
      </div>
    </RoleGuard>
  );
}
