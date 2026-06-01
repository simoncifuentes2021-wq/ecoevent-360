"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { ServiceForm } from "@/components/services/ServiceForm";
import { Button } from "@/components/ui/button";
import { deleteService, getService, updateService } from "@/lib/api/services";
import type { Service, ServiceCreate, ServiceUpdate } from "@/types/service";

export default function EditServicePage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const [service, setService] = useState<Service | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setService(await getService(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el servicio.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: ServiceCreate | ServiceUpdate) {
    await updateService(params.id, data as ServiceUpdate);
    router.push("/admin/servicios");
  }

  async function deactivate() {
    await deleteService(params.id);
    router.push("/admin/servicios");
  }

  if (loading) return <LoadingState label="Cargando servicio..." />;
  if (error || !service) return <ErrorState message={error || "Servicio no encontrado"} title="No pudimos cargar el servicio" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Editar servicio"
          description={service.name}
          actions={
            service.is_active ? (
              <Button variant="secondary" onClick={() => setConfirmOpen(true)}>
                Desactivar
              </Button>
            ) : null
          }
        />
        <ServiceForm cancelHref="/admin/servicios" service={service} submitLabel="Guardar cambios" onSubmit={submit} />
        <ConfirmDialog
          description="El servicio quedara inactivo, manteniendo su historial."
          open={confirmOpen}
          title="Desactivar servicio"
          onClose={() => setConfirmOpen(false)}
          onConfirm={deactivate}
        />
      </div>
    </RoleGuard>
  );
}
