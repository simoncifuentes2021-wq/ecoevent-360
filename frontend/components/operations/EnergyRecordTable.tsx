"use client";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import type { EnergyRecord } from "@/types/operations";
export function EnergyRecordTable({ records }: { records: EnergyRecord[] }) {
  const columns: DataTableColumn<EnergyRecord>[] = [
    { key: "date", header: "Fecha", cell: (r) => r.recorded_at ? new Date(r.recorded_at).toLocaleDateString("es-CL") : "-" },
    { key: "source", header: "Fuente", cell: (r) => r.energy_source },
    { key: "kwh", header: "kWh", cell: (r) => Number(r.kwh || 0).toLocaleString("es-CL") },
    { key: "zone", header: "Zona", cell: (r) => r.zone?.name || "-" }
  ];
  return <DataTable columns={columns} data={records} emptyTitle="Sin energia" emptyDescription="Registra consumos electricos del evento." getRowKey={(r) => r.id} />;
}
