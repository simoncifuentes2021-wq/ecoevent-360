"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ClientForm } from "@/components/clients/ClientForm";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { deleteClient, getClient, updateClient } from "@/lib/api/clients";
import type { Client, ClientCreate, ClientUpdate } from "@/types/client";

export default function EditClientPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [client, setClient] = useState<Client | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setClient(await getClient(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el cliente.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: ClientCreate | ClientUpdate) {
    await updateClient(params.id, data as ClientUpdate);
    router.push(`/admin/clientes/${params.id}`);
  }

  async function deactivate() {
    await deleteClient(params.id);
    router.push("/admin/clientes");
  }

  if (loading) return <LoadingState label="Cargando cliente..." />;
  if (error || !client) return <ErrorState message={error || "Cliente no encontrado"} title="No pudimos cargar el cliente" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Editar cliente"
          description={client.business_name}
          actions={
            client.is_active ? (
              <Button variant="secondary" onClick={() => setConfirmOpen(true)}>
                Desactivar
              </Button>
            ) : null
          }
        />
        <ClientForm cancelHref={`/admin/clientes/${params.id}`} client={client} submitLabel="Guardar cambios" onSubmit={submit} />
        <ConfirmDialog
          description="El cliente quedara inactivo, manteniendo su historial y eventos."
          open={confirmOpen}
          title="Desactivar cliente"
          onClose={() => setConfirmOpen(false)}
          onConfirm={deactivate}
        />
      </div>
    </RoleGuard>
  );
}
