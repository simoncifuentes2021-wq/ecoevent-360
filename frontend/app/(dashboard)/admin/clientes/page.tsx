"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { ClientFilters } from "@/components/clients/ClientFilters";
import { ClientTable } from "@/components/clients/ClientTable";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { deleteClient, getClients } from "@/lib/api/clients";
import type { Client } from "@/types/client";

const limit = 20;

export default function AdminClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [q, setQ] = useState("");
  const [isActive, setIsActive] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [selected, setSelected] = useState<Client | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await getClients({ q, is_active: isActive || undefined, page, limit });
      setClients(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los clientes.");
    } finally {
      setLoading(false);
    }
  }, [q, isActive, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function confirmDeactivate() {
    if (!selected) return;
    await deleteClient(selected.id);
    setSelected(null);
    await load();
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Clientes"
          description="Gestiona empresas, contactos comerciales y estado de relacion operacional."
          actions={
            <Link href="/admin/clientes/nuevo">
              <Button>
                <Plus className="h-4 w-4" />
                Crear cliente
              </Button>
            </Link>
          }
        />
        <ClientFilters
          active={isActive}
          q={q}
          onActiveChange={(value: string) => {
            setIsActive(value);
            setPage(1);
          }}
          onQChange={(value) => {
            setQ(value);
            setPage(1);
          }}
        />
        <ClientTable
          clients={clients}
          error={error || null}
          limit={limit}
          loading={loading}
          page={page}
          total={total}
          onDeactivate={setSelected}
          onPageChange={setPage}
        />
        <ConfirmDialog
          description={`El cliente ${selected?.business_name || ""} quedara inactivo, sin eliminar su historial.`}
          open={Boolean(selected)}
          title="Desactivar cliente"
          onClose={() => setSelected(null)}
          onConfirm={confirmDeactivate}
        />
      </div>
    </RoleGuard>
  );
}
