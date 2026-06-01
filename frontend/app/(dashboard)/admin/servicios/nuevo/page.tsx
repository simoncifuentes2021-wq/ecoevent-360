"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { ServiceForm } from "@/components/services/ServiceForm";
import { createService } from "@/lib/api/services";
import type { ServiceCreate, ServiceUpdate } from "@/types/service";

export default function NewServicePage() {
  const router = useRouter();

  async function submit(data: ServiceCreate | ServiceUpdate) {
    await createService(data as ServiceCreate);
    router.push("/admin/servicios");
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader title="Crear servicio" description="Agrega un servicio al catalogo comercial y operativo." />
        <ServiceForm cancelHref="/admin/servicios" submitLabel="Crear servicio" onSubmit={submit} />
      </div>
    </RoleGuard>
  );
}
