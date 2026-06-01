"use client";

import { useRouter } from "next/navigation";

import { ClientForm } from "@/components/clients/ClientForm";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { createClient } from "@/lib/api/clients";
import type { ClientCreate, ClientUpdate } from "@/types/client";

export default function NewClientPage() {
  const router = useRouter();

  async function submit(data: ClientCreate | ClientUpdate) {
    const client = await createClient(data as ClientCreate);
    router.push(`/admin/clientes/${client.id}`);
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader title="Crear cliente" description="Registra una empresa cliente para asociar eventos y usuarios." />
        <ClientForm cancelHref="/admin/clientes" submitLabel="Crear cliente" onSubmit={submit} />
      </div>
    </RoleGuard>
  );
}
