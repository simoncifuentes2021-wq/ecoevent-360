"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

type ServiceFiltersProps = {
  q: string;
  isActive: string;
  onQChange: (value: string) => void;
  onIsActiveChange: (value: string) => void;
};

export function ServiceFilters({ q, isActive, onQChange, onIsActiveChange }: ServiceFiltersProps) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_180px]">
      <SearchInput
        placeholder="Buscar por nombre, categoria o unidad..."
        value={q}
        onChange={onQChange}
      />
      <FilterSelect
        label="Estado"
        value={isActive}
        onChange={onIsActiveChange}
        options={[
          { label: "Todos", value: "" },
          { label: "Activos", value: "true" },
          { label: "Inactivos", value: "false" }
        ]}
      />
    </div>
  );
}
