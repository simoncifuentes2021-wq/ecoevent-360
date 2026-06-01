import { Badge } from "@/components/ui/badge";
import type { WasteTypeCode } from "@/types/waste";

const labels: Record<WasteTypeCode, string> = {
  PLASTIC: "Plastico",
  CARDBOARD: "Carton/Papel",
  GLASS: "Vidrio",
  ALUMINUM: "Aluminio",
  ORGANIC: "Organico",
  GENERAL: "General",
  HAZARDOUS: "Peligroso",
  OTHER: "Otro"
};

export function WasteTypeBadge({ value }: { value?: string | null }) {
  return <Badge tone={value === "HAZARDOUS" ? "danger" : value === "ORGANIC" ? "success" : "neutral"}>{labels[value as WasteTypeCode] || value || "Sin tipo"}</Badge>;
}
