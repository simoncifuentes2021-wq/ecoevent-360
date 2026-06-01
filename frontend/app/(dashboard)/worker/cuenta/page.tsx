import { UserRound } from "lucide-react";

import { ModulePlaceholder } from "@/components/common/ModulePlaceholder";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function WorkerAccountPage() {
  return (
    <RoleGuard roles={["WORKER"]}>
      <ModulePlaceholder
        description="Consulta tu perfil operativo y datos de contacto."
        eyebrow="Trabajo en terreno"
        icon={UserRound}
        title="Mi cuenta"
      />
    </RoleGuard>
  );
}
