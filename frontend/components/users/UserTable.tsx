import Link from "next/link";
import { Pencil, Power } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { RoleBadge } from "@/components/common/RoleBadge";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import type { User } from "@/types/user";

export function UserTable({
  users,
  loading,
  error,
  page,
  limit,
  total,
  onPageChange,
  onDeactivate
}: {
  users: User[];
  loading: boolean;
  error: string | null;
  page: number;
  limit: number;
  total: number;
  onPageChange: (page: number) => void;
  onDeactivate: (user: User) => void;
}) {
  const columns: DataTableColumn<User>[] = [
    { key: "name", header: "Nombre", cell: (user) => <span className="font-semibold">{user.full_name}</span> },
    { key: "email", header: "Email", cell: (user) => user.email },
    { key: "phone", header: "Teléfono", cell: (user) => user.phone ?? "Sin teléfono" },
    { key: "role", header: "Rol", cell: (user) => <RoleBadge role={user.role} /> },
    { key: "client", header: "Cliente", cell: (user) => user.client?.business_name ?? user.client_id ?? "Sin cliente" },
    { key: "status", header: "Estado", cell: (user) => <StatusBadge status={user.is_active ? "ACTIVE" : "INACTIVE"} /> },
    {
      key: "actions",
      header: "Acciones",
      cell: (user) => (
        <div className="flex gap-2">
          <Link href={`/admin/usuarios/${user.id}/editar`}>
            <Button className="h-8 px-2" type="button" variant="ghost">
              <Pencil className="h-4 w-4" />
            </Button>
          </Link>
          <Button className="h-8 px-2" onClick={() => onDeactivate(user)} type="button" variant="ghost">
            <Power className="h-4 w-4" />
          </Button>
        </div>
      )
    }
  ];

  return (
    <DataTable
      columns={columns}
      data={users}
      emptyDescription="Crea usuarios para administrar clientes, supervisores y trabajadores."
      emptyTitle="No hay usuarios"
      error={error}
      limit={limit}
      loading={loading}
      onPageChange={onPageChange}
      page={page}
      total={total}
    />
  );
}
