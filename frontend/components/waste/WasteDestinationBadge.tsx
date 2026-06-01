import { Badge } from "@/components/ui/badge";
import type { WasteDestination } from "@/types/waste";

const labels: Record<WasteDestination, string> = {
  RECYCLING: "Reciclaje",
  COMPOSTING: "Compostaje",
  LANDFILL: "Relleno sanitario",
  RECOVERY: "Recuperacion",
  SPECIAL_DISPOSAL: "Disposicion especial",
  OTHER: "Otro"
};

export function WasteDestinationBadge({ destination }: { destination: WasteDestination }) {
  const tone = destination === "LANDFILL" || destination === "SPECIAL_DISPOSAL" ? "warning" : destination === "OTHER" ? "neutral" : "success";
  return <Badge tone={tone}>{labels[destination] || destination}</Badge>;
}
