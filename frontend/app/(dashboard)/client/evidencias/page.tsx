import { Camera } from "lucide-react";

import { ModulePlaceholder } from "@/components/common/ModulePlaceholder";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function ClientEvidencePage() {
  return (
    <RoleGuard roles={["CLIENT"]}>
      <ModulePlaceholder
        description="Explora evidencias fotográficas y documentos asociados a tus eventos."
        eyebrow="Portal cliente"
        icon={Camera}
        title="Evidencias"
      />
    </RoleGuard>
  );
}
