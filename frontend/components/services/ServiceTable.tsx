"use client";

import Link from "next/link";
import { Edit, Power } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import type { Service } from "@/types/service";

type ServiceTableProps = {
  services: Service[];
  loading?: boolean;
  error?: string;
  page: number;
  limit: number;
  total: number;
  onPageChange: (page: number) => void;
  onDeactivate: (service: Service) => void;
};

export function ServiceTable(props: ServiceTableProps) {
  const columns: DataTableColumn<Service>[] = [
    { key: "name", header: "Servicio", cell: (service) => <span className="font-semibold">{service.name}</span> },
    { key: "category", header: "Categoria", cell: (service) => service.category || "Sin categoria" },
    { key: "unit", header: "Unidad", cell: (service) => service.unit || "-" },
    {
      key: "base_price",
      header: "Precio base",
      cell: (service) => Number(service.base_price || 0).toLocaleString("es-CL", { style: "currency", currency: "CLP" })
    },
    { key: "is_active", header: "Estado", cell: (service) => <StatusBadge status={service.is_active ? "ACTIVE" : "INACTIVE"} /> }
  ];

  return (
    <DataTable
      actions={(service) => (
        <div className="flex justify-end gap-2">
          <Link href={`/admin/servicios/${service.id}/editar`}>
            <Button size="sm" variant="secondary">
              <Edit className="h-4 w-4" />
            </Button>
          </Link>
          {service.is_active ? (
            <Button size="sm" variant="ghost" onClick={() => props.onDeactivate(service)}>
              <Power className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      )}
      columns={columns}
      data={props.services}
      emptyTitle="Sin servicios"
      error={props.error}
      getRowKey={(service) => service.id}
      limit={props.limit}
      loading={props.loading}
      onPageChange={props.onPageChange}
      page={props.page}
      total={props.total}
    />
  );
}
