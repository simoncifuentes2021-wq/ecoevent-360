"use client";

import Link from "next/link";
import { CalendarClock, Edit, Eye, Power } from "lucide-react";

import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Button } from "@/components/ui/button";
import type { Event } from "@/types/event";

type EventTableProps = {
  events: Event[];
  loading?: boolean;
  error?: string;
  page: number;
  limit: number;
  total: number;
  onPageChange: (page: number) => void;
  onChangeStatus: (event: Event) => void;
  onCancel: (event: Event) => void;
};

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value));
}

export function EventTable(props: EventTableProps) {
  const columns: DataTableColumn<Event>[] = [
    {
      key: "name",
      header: "Evento",
      cell: (event) => (
        <div>
          <p className="font-semibold text-slate-950">{event.name}</p>
          <p className="text-xs text-slate-500">{event.event_type || "Sin tipo"}</p>
        </div>
      )
    },
    { key: "client", header: "Cliente", cell: (event) => event.client?.business_name || "Sin cliente" },
    { key: "status", header: "Estado", cell: (event) => <EventStatusBadge status={event.status} /> },
    { key: "city", header: "Ciudad/region", cell: (event) => [event.city, event.region].filter(Boolean).join(", ") || "-" },
    { key: "start_date", header: "Inicio", cell: (event) => formatDate(event.start_date) },
    { key: "end_date", header: "Termino", cell: (event) => formatDate(event.end_date) },
    { key: "estimated_attendees", header: "Asistentes", cell: (event) => event.estimated_attendees?.toLocaleString("es-CL") || "0" }
  ];

  return (
    <DataTable
      actions={(event) => (
        <div className="flex justify-end gap-2">
          <Link href={`/admin/eventos/${event.id}`}>
            <Button size="sm" variant="secondary">
              <Eye className="h-4 w-4" />
            </Button>
          </Link>
          <Button size="sm" variant="ghost" onClick={() => props.onChangeStatus(event)}>
            <CalendarClock className="h-4 w-4" />
          </Button>
          <Link href={`/admin/eventos/${event.id}/editar`}>
            <Button size="sm" variant="secondary">
              <Edit className="h-4 w-4" />
            </Button>
          </Link>
          {event.status !== "CANCELLED" ? (
            <Button size="sm" variant="ghost" onClick={() => props.onCancel(event)}>
              <Power className="h-4 w-4" />
            </Button>
          ) : null}
        </div>
      )}
      columns={columns}
      data={props.events}
      emptyTitle="Sin eventos"
      error={props.error}
      getRowKey={(event) => event.id}
      limit={props.limit}
      loading={props.loading}
      onPageChange={props.onPageChange}
      page={props.page}
      total={props.total}
    />
  );
}
