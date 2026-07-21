import { Badge } from "@/components/ui/badge";
import { getCarbonCategoryLabel, normalizeCarbonCategory } from "@/components/carbon/CarbonFilters";

export function CarbonCategoryBadge({ category }: { category?: string | null }) {
  const normalized = normalizeCarbonCategory(category);
  return <Badge tone={normalized === "ENERGY" ? "success" : normalized === "TRANSPORT" ? "warning" : "neutral"}>{getCarbonCategoryLabel(category)}</Badge>;
}
