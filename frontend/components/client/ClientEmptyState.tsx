import { Sparkles } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";

export function ClientEmptyState({ title = "Aun no hay informacion disponible", description = "Cuando existan datos asociados a tu cliente, apareceran aqui." }: { title?: string; description?: string }) {
  return <EmptyState icon={<Sparkles className="h-10 w-10" />} title={title} description={description} />;
}
