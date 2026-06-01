import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export function ClientFilters({
  q,
  active,
  onQChange,
  onActiveChange
}: {
  q: string;
  active: string;
  onQChange: (value: string) => void;
  onActiveChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-[1fr_220px]">
      <SearchInput onChange={onQChange} placeholder="Buscar por razón social, RUT, contacto o email" value={q} />
      <FilterSelect
        label="Estado"
        onChange={onActiveChange}
        options={[
          { label: "Todos", value: "" },
          { label: "Activos", value: "true" },
          { label: "Inactivos", value: "false" }
        ]}
        value={active}
      />
    </div>
  );
}
