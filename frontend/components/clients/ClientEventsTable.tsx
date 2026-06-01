import Link from "next/link";
import { Eye } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Button } from "@/components/ui/button";
import type { ClientEvent } from "@/types/client";

export function ClientEventsTable({ events }: { events: ClientEvent[] }) {
  const columns: DataTableColumn<ClientEvent>[] = [
    { key: "name", header: "Evento", cell: (event) => <span className="font-semibold">{event.name}</span> },
    { key: "type", header: "Tipo", cell: (event) => event.event_type ?? "Sin tipo" },
    { key: "start", header: "Inicio", cell: (event) => new Date(event.start_date).toLocaleDateString("es-CL") },
    { key: "end", header: "Termino", cell: (event) => new Date(event.end_date).toLocaleDateString("es-CL") },
    { key: "status", header: "Estado", cell: (event) => <StatusBadge status={event.status} /> }
  ];

  return (
    <DataTable
      actions={(event) => (
        <div className="flex justify-end">
          <Link href={`/admin/eventos/${event.id}`}>
            <Button size="sm" type="button" variant="secondary">
              <Eye className="h-4 w-4" />
              Ver
            </Button>
          </Link>
        </div>
      )}
      columns={columns}
      data={events}
      emptyDescription="Este cliente todavia no tiene eventos registrados."
      emptyTitle="Sin eventos asociados"
      getRowKey={(event) => event.id}
    />
  );
}
