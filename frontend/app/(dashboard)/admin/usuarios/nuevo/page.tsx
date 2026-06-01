"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { UserForm } from "@/components/users/UserForm";
import { useAuth } from "@/hooks/useAuth";
import { getClients } from "@/lib/api/clients";
import { createUser } from "@/lib/api/users";
import type { Client } from "@/types/client";
import type { UserCreate, UserUpdate } from "@/types/user";

export default function NewUserPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadClients = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getClients({ is_active: "true", page: 1, limit: 100 });
      setClients(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar clientes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadClients();
  }, [loadClients]);

  async function submit(data: UserCreate | UserUpdate) {
    await createUser(data as UserCreate);
    router.push("/admin/usuarios");
  }

  if (loading) return <LoadingState label="Cargando clientes..." />;
  if (error) return <ErrorState message={error} title="No pudimos preparar el formulario" onRetry={loadClients} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader title="Crear usuario" description="Define credenciales, rol y asociacion con cliente cuando corresponda." />
        <UserForm cancelHref="/admin/usuarios" clients={clients} currentRole={user?.role || "ADMIN"} submitLabel="Crear usuario" onSubmit={submit} />
      </div>
    </RoleGuard>
  );
}
