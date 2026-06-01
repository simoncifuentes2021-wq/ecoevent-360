"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { ServiceFilters } from "@/components/services/ServiceFilters";
import { ServiceTable } from "@/components/services/ServiceTable";
import { Button } from "@/components/ui/button";
import { deleteService, getServices } from "@/lib/api/services";
import type { Service } from "@/types/service";

const limit = 20;

export default function AdminServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [q, setQ] = useState("");
  const [isActive, setIsActive] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [selected, setSelected] = useState<Service | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await getServices({ q, is_active: isActive || undefined, page, limit });
      setServices(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los servicios.");
    } finally {
      setLoading(false);
    }
  }, [q, isActive, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function confirmDeactivate() {
    if (!selected) return;
    await deleteService(selected.id);
    setSelected(null);
    await load();
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Servicios"
          description="Catalogo base para propuestas, contrataciones y control operativo por evento."
          actions={
            <Link href="/admin/servicios/nuevo">
              <Button>
                <Plus className="h-4 w-4" />
                Crear servicio
              </Button>
            </Link>
          }
        />
        <ServiceFilters
          isActive={isActive}
          q={q}
          onIsActiveChange={(value) => {
            setIsActive(value);
            setPage(1);
          }}
          onQChange={(value) => {
            setQ(value);
            setPage(1);
          }}
        />
        <ServiceTable
          error={error}
          limit={limit}
          loading={loading}
          page={page}
          services={services}
          total={total}
          onDeactivate={setSelected}
          onPageChange={setPage}
        />
        <ConfirmDialog
          description={`El servicio ${selected?.name || ""} quedara inactivo para nuevas contrataciones.`}
          open={Boolean(selected)}
          title="Desactivar servicio"
          onClose={() => setSelected(null)}
          onConfirm={confirmDeactivate}
        />
      </div>
    </RoleGuard>
  );
}
