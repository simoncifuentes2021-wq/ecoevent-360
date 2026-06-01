import { Badge } from "@/components/ui/badge";

const labels: Record<string, string> = {
  TRANSPORT: "Transporte",
  ENERGY: "Energia",
  WASTE: "Residuos",
  WATER: "Agua",
  MATERIALS: "Materiales",
  FOOD: "Alimentacion",
  ACCOMMODATION: "Alojamiento",
  OTHER: "Otro"
};
export function CarbonCategoryBadge({ category }: { category?: string | null }) {
  return <Badge tone={category === "ENERGY" ? "success" : category === "TRANSPORT" ? "warning" : "neutral"}>{labels[category || "OTHER"] || category}</Badge>;
}
