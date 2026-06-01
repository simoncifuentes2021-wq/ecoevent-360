import { ShieldCheck } from "lucide-react";

import { ModulePlaceholder } from "@/components/common/ModulePlaceholder";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function AlertsPage() {
  return (
    <RoleGuard roles={["SUPERVISOR"]}>
      <ModulePlaceholder
        description="Revisa alertas operativas generadas por incidencias, residuos o encuestas."
        eyebrow="Supervisión"
        icon={ShieldCheck}
        title="Alertas"
      />
    </RoleGuard>
  );
}
