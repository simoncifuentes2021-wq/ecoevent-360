import { Badge } from "@/components/ui/badge";
import type { Priority } from "@/types/task";

export function PriorityBadge({ priority }: { priority: Priority }) {
  const isCritical = priority === "CRITICAL";
  const label = isCritical ? "Critica" : priority === "HIGH" ? "Alta" : priority === "MEDIUM" ? "Media" : "Baja";
  const tone = isCritical ? "danger" : priority === "HIGH" ? "warning" : priority === "MEDIUM" ? "neutral" : "success";
  return <Badge tone={tone}>{label}</Badge>;
}
