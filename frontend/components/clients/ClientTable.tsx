import Link from "next/link";
import { Eye, Pencil, Power } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import type { Client } from "@/types/client";

export function ClientTable({
  clients,
  loading,
  error,
  page,
  limit,
  total,
  onPageChange,
  onDeactivate
}: {
  clients: Client[];
  loading: boolean;
  error: string | null;
  page: number;
  limit: number;
  total: number;
  onPageChange: (page: number) => void;
  onDeactivate: (client: Client) => void;
}) {
  const columns: DataTableColumn<Client>[] = [
    {
      key: "business_name",
      header: "Razón social",
      cell: (client) => <span className="font-semibold">{client.business_name}</span>
    },
    { key: "rut", header: "RUT", cell: (client) => client.rut ?? "Sin RUT" },
    { key: "contact", header: "Contacto", cell: (client) => client.contact_name ?? "Sin contacto" },
    { key: "email", header: "Email", cell: (client) => client.contact_email ?? "Sin email" },
    { key: "phone", header: "Teléfono", cell: (client) => client.contact_phone ?? "Sin teléfono" },
    {
      key: "status",
      header: "Estado",
      cell: (client) => <StatusBadge status={client.is_active ? "ACTIVE" : "INACTIVE"} />
    },
    {
      key: "actions",
      header: "Acciones",
      cell: (client) => (
        <div className="flex gap-2">
          <Link href={`/admin/clientes/${client.id}`}>
            <Button className="h-8 px-2" type="button" variant="ghost">
              <Eye className="h-4 w-4" />
            </Button>
          </Link>
          <Link href={`/admin/clientes/${client.id}/editar`}>
            <Button className="h-8 px-2" type="button" variant="ghost">
              <Pencil className="h-4 w-4" />
            </Button>
          </Link>
          <Button className="h-8 px-2" onClick={() => onDeactivate(client)} type="button" variant="ghost">
            <Power className="h-4 w-4" />
          </Button>
        </div>
      )
    }
  ];

  return (
    <DataTable
      columns={columns}
      data={clients}
      emptyDescription="Crea el primer cliente para comenzar a gestionar eventos."
      emptyTitle="No hay clientes"
      error={error}
      limit={limit}
      loading={loading}
      onPageChange={onPageChange}
      page={page}
      total={total}
    />
  );
}
