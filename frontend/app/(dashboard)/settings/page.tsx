import { Settings } from "lucide-react";

import { ModulePlaceholder } from "@/components/common/ModulePlaceholder";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function SettingsPage() {
  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <ModulePlaceholder
        description="Configura parámetros generales, integraciones y preferencias operativas."
        eyebrow="Sistema"
        icon={Settings}
        title="Configuración"
      />
    </RoleGuard>
  );
}
