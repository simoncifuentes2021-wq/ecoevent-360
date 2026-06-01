"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { PageHeader } from "@/components/common/PageHeader";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { UserFilters } from "@/components/users/UserFilters";
import { UserTable } from "@/components/users/UserTable";
import { Button } from "@/components/ui/button";
import { deleteUser, getUsers } from "@/lib/api/users";
import type { User } from "@/types/user";

const limit = 20;

export default function AdminUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [q, setQ] = useState("");
  const [role, setRole] = useState("");
  const [isActive, setIsActive] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | undefined>();
  const [selected, setSelected] = useState<User | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(undefined);
    try {
      const response = await getUsers({ q, role: role || undefined, is_active: isActive || undefined, page, limit });
      setUsers(response.items);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar los usuarios.");
    } finally {
      setLoading(false);
    }
  }, [q, role, isActive, page]);

  useEffect(() => {
    void load();
  }, [load]);

  async function confirmDeactivate() {
    if (!selected) return;
    await deleteUser(selected.id);
    setSelected(null);
    await load();
  }

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Usuarios"
          description="Administra accesos, roles y asociacion con clientes."
          actions={
            <Link href="/admin/usuarios/nuevo">
              <Button>
                <Plus className="h-4 w-4" />
                Crear usuario
              </Button>
            </Link>
          }
        />
        <UserFilters
          active={isActive}
          q={q}
          role={role}
          onActiveChange={(value: string) => {
            setIsActive(value);
            setPage(1);
          }}
          onQChange={(value) => {
            setQ(value);
            setPage(1);
          }}
          onRoleChange={(value) => {
            setRole(value);
            setPage(1);
          }}
        />
        <UserTable
          error={error || null}
          limit={limit}
          loading={loading}
          page={page}
          total={total}
          users={users}
          onDeactivate={setSelected}
          onPageChange={setPage}
        />
        <ConfirmDialog
          description={`El usuario ${selected?.full_name || ""} quedara inactivo y no podra iniciar sesion.`}
          open={Boolean(selected)}
          title="Desactivar usuario"
          onClose={() => setSelected(null)}
          onConfirm={confirmDeactivate}
        />
      </div>
    </RoleGuard>
  );
}
