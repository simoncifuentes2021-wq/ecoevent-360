"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { UserForm } from "@/components/users/UserForm";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { getClients } from "@/lib/api/clients";
import { deleteUser, getUser, updateUser } from "@/lib/api/users";
import type { Client } from "@/types/client";
import type { User, UserCreate, UserUpdate } from "@/types/user";

export default function EditUserPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const { user: currentUser } = useAuth();
  const [user, setUser] = useState<User | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [userData, clientData] = await Promise.all([getUser(params.id), getClients({ is_active: "true", page: 1, limit: 100 })]);
      setUser(userData);
      setClients(clientData.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el usuario.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(data: UserCreate | UserUpdate) {
    await updateUser(params.id, data as UserUpdate);
    router.push("/admin/usuarios");
  }

  async function deactivate() {
    await deleteUser(params.id);
    router.push("/admin/usuarios");
  }

  if (loading) return <LoadingState label="Cargando usuario..." />;
  if (error || !user) return <ErrorState message={error || "Usuario no encontrado"} title="No pudimos cargar el usuario" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Editar usuario"
          description={user.email}
          actions={
            user.is_active ? (
              <Button variant="secondary" onClick={() => setConfirmOpen(true)}>
                Desactivar
              </Button>
            ) : null
          }
        />
        <UserForm
          cancelHref="/admin/usuarios"
          clients={clients}
          currentRole={currentUser?.role || "ADMIN"}
          submitLabel="Guardar cambios"
          user={user}
          onSubmit={submit}
        />
        <ConfirmDialog
          description="El usuario quedara inactivo y perdera acceso a la plataforma."
          open={confirmOpen}
          title="Desactivar usuario"
          onClose={() => setConfirmOpen(false)}
          onConfirm={deactivate}
        />
      </div>
    </RoleGuard>
  );
}
