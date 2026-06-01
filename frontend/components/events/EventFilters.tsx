"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";
import type { Client } from "@/types/client";
import type { EventStatus } from "@/types/event";

type EventFiltersProps = {
  q: string;
  status: string;
  clientId: string;
  clients: Client[];
  onQChange: (value: string) => void;
  onStatusChange: (value: string) => void;
  onClientChange: (value: string) => void;
};

const statusOptions: Array<{ label: string; value: "" | EventStatus }> = [
  { label: "Todos", value: "" },
  { label: "Cotizacion", value: "QUOTE" },
  { label: "Planificacion", value: "PLANNING" },
  { label: "En curso", value: "IN_PROGRESS" },
  { label: "Finalizado", value: "FINISHED" },
  { label: "Reporte entregado", value: "REPORT_DELIVERED" },
  { label: "Cancelado", value: "CANCELLED" }
];

export function EventFilters(props: EventFiltersProps) {
  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_220px_220px]">
      <SearchInput placeholder="Buscar por evento, ciudad o ubicacion..." value={props.q} onChange={props.onQChange} />
      <FilterSelect label="Estado" value={props.status} onChange={props.onStatusChange} options={statusOptions} />
      <FilterSelect
        label="Cliente"
        value={props.clientId}
        onChange={props.onClientChange}
        options={[{ label: "Todos", value: "" }, ...props.clients.map((client) => ({ label: client.business_name, value: client.id }))]}
      />
    </div>
  );
}
