"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

import type { EventSession } from "@/types/eventSession";

export function EvidenceFilters({ q, type, context, sessions, onQChange, onTypeChange, onContextChange }: { q: string; type: string; context: string; sessions: EventSession[]; onQChange: (value: string) => void; onTypeChange: (value: string) => void; onContextChange: (value: string) => void }) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_180px_220px]">
      <SearchInput placeholder="Buscar por descripcion..." value={q} onChange={onQChange} />
      <FilterSelect label="Tipo" value={type} onChange={onTypeChange} options={[{ label: "Todos", value: "" }, { label: "Imagen", value: "image" }, { label: "PDF", value: "pdf" }]} />
      <FilterSelect label="Contexto" value={context} onChange={onContextChange} options={[{ label: "Todas", value: "all" }, { label: "General", value: "general" }, ...sessions.map((session) => ({ label: session.name, value: session.id }))]} />
    </div>
  );
}
