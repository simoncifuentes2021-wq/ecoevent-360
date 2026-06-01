"use client";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import type { WaterRecord } from "@/types/operations";
export function WaterRecordTable({ records }: { records: WaterRecord[] }) {
  const columns: DataTableColumn<WaterRecord>[] = [
    { key: "date", header: "Fecha", cell: (r) => r.recorded_at ? new Date(r.recorded_at).toLocaleDateString("es-CL") : "-" },
    { key: "source", header: "Fuente", cell: (r) => r.water_source },
    { key: "m3", header: "m3", cell: (r) => Number(r.volume_m3 || 0).toLocaleString("es-CL") },
    { key: "zone", header: "Zona", cell: (r) => r.zone?.name || "-" }
  ];
  return <DataTable columns={columns} data={records} emptyTitle="Sin agua" emptyDescription="Registra consumos de agua del evento." getRowKey={(r) => r.id} />;
}
