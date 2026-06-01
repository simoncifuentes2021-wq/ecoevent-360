"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export function SurveyFilters({ q, status, onQChange, onStatusChange }: { q: string; status: string; onQChange: (value: string) => void; onStatusChange: (value: string) => void }) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_220px]">
      <SearchInput value={q} onChange={onQChange} placeholder="Buscar por titulo o descripcion" />
      <FilterSelect label="Estado" value={status} onChange={onStatusChange} options={[{ label: "Todos", value: "" }, { label: "Borrador", value: "DRAFT" }, { label: "Activa", value: "ACTIVE" }, { label: "Cerrada", value: "CLOSED" }, { label: "Archivada", value: "ARCHIVED" }]} />
    </div>
  );
}
