import { Users } from "lucide-react";

import { ModulePlaceholder } from "@/components/common/ModulePlaceholder";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function UsersPage() {
  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <ModulePlaceholder
        description="Administra cuentas, roles y accesos del equipo y clientes."
        eyebrow="Administración"
        icon={Users}
        title="Usuarios"
      />
    </RoleGuard>
  );
}
