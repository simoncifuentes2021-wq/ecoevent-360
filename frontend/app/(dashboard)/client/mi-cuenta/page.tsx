"use client";

import { useEffect, useState } from "react";

import { ClientAccountPage } from "@/components/client/ClientAccountPage";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { useAuth } from "@/hooks/useAuth";
import { getClient } from "@/lib/api/clients";
import type { Client } from "@/types/client";

export default function ClientAccountRoute() {
  const { user, loading: authLoading } = useAuth();
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      if (!user?.client_id) return;
      setLoading(true);
      setError(null);
      try {
        setClient(await getClient(user.client_id));
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo cargar la empresa asociada.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [user?.client_id]);

  return (
    <RoleGuard roles={["CLIENT"]}>
      <div className="space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase text-primary">Portal cliente</p>
          <h1 className="mt-1 text-3xl font-bold">Mi cuenta</h1>
          <p className="mt-2 text-muted-foreground">Datos de usuario y empresa asociada.</p>
        </div>
        {authLoading || loading ? <LoadingState label="Cargando cuenta..." /> : null}
        {error ? <ErrorState message={error} /> : null}
        {user && !authLoading && !loading ? <ClientAccountPage client={client} user={user} /> : null}
      </div>
    </RoleGuard>
  );
}
