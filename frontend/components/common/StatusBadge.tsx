import { Badge } from "@/components/ui/badge";
import { statusLabel } from "@/lib/status-labels";

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status.includes("FINISHED") || status.includes("COMPLETED") || status.includes("ACTIVE")
      ? "success"
      : status.includes("CANCELLED") || status.includes("CLOSED")
        ? "danger"
        : "warning";
  return <Badge tone={tone}>{statusLabel(status)}</Badge>;
}
