"use client";
import { DataTable, type DataTableColumn } from "@/components/common/DataTable";
import type { FuelRecord } from "@/types/operations";
export function FuelRecordTable({ records }: { records: FuelRecord[] }) {
  const columns: DataTableColumn<FuelRecord>[] = [
    { key: "date", header: "Fecha", cell: (r) => r.recorded_at ? new Date(r.recorded_at).toLocaleDateString("es-CL") : "-" },
    { key: "type", header: "Combustible", cell: (r) => r.fuel_type },
    { key: "qty", header: "Cantidad", cell: (r) => `${r.quantity} ${r.unit}` },
    { key: "equipment", header: "Equipo", cell: (r) => r.vehicle_or_equipment || "-" },
    { key: "zone", header: "Zona", cell: (r) => r.zone?.name || "-" }
  ];
  return <DataTable columns={columns} data={records} emptyTitle="Sin combustible" emptyDescription="Registra combustible usado por equipos o vehiculos." getRowKey={(r) => r.id} />;
}
