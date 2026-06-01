"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export function EvidenceFilters({ q, type, onQChange, onTypeChange }: { q: string; type: string; onQChange: (value: string) => void; onTypeChange: (value: string) => void }) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_180px]">
      <SearchInput placeholder="Buscar por descripcion..." value={q} onChange={onQChange} />
      <FilterSelect label="Tipo" value={type} onChange={onTypeChange} options={[{ label: "Todos", value: "" }, { label: "Imagen", value: "image" }, { label: "PDF", value: "pdf" }]} />
    </div>
  );
}
