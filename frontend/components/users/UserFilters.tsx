import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export function UserFilters({
  q,
  role,
  active,
  onQChange,
  onRoleChange,
  onActiveChange
}: {
  q: string;
  role: string;
  active: string;
  onQChange: (value: string) => void;
  onRoleChange: (value: string) => void;
  onActiveChange: (value: string) => void;
}) {
  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_220px_220px]">
      <SearchInput onChange={onQChange} placeholder="Buscar por nombre o email" value={q} />
      <FilterSelect
        label="Rol"
        onChange={onRoleChange}
        options={[
          { label: "Todos", value: "" },
          { label: "Super admin", value: "SUPER_ADMIN" },
          { label: "Admin", value: "ADMIN" },
          { label: "Cliente", value: "CLIENT" },
          { label: "Supervisor", value: "SUPERVISOR" },
          { label: "Trabajador", value: "WORKER" }
        ]}
        value={role}
      />
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
