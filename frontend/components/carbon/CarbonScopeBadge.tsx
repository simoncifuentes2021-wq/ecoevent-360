import { Badge } from "@/components/ui/badge";
import type { CarbonScope } from "@/types/carbon";

const labels: Record<CarbonScope, string> = { SCOPE_1: "Alcance 1", SCOPE_2: "Alcance 2", SCOPE_3: "Alcance 3" };
export function CarbonScopeBadge({ scope }: { scope?: CarbonScope | null }) {
  return <Badge tone={scope === "SCOPE_1" ? "warning" : scope === "SCOPE_2" ? "success" : "neutral"}>{scope ? labels[scope] : "Sin alcance"}</Badge>;
}
