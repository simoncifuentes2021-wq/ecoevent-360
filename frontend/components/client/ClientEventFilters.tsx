"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export function ClientEventFilters({ q, status, onQChange, onStatusChange }: { q: string; status: string; onQChange: (value: string) => void; onStatusChange: (value: string) => void }) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_240px]">
      <SearchInput value={q} onChange={onQChange} placeholder="Buscar evento por nombre, ciudad o tipo" />
      <FilterSelect label="Estado" value={status} onChange={onStatusChange} options={[{ label: "Todos", value: "" }, { label: "Planificacion", value: "PLANNING" }, { label: "En progreso", value: "IN_PROGRESS" }, { label: "Finalizado", value: "FINISHED" }, { label: "Reporte entregado", value: "REPORT_DELIVERED" }, { label: "Cancelado", value: "CANCELLED" }]} />
    </div>
  );
}
