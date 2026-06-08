import { Badge } from "@/components/ui/badge";
import { eventStatusLabels } from "@/lib/status-labels";
import type { EventStatus } from "@/types/event";

export function EventStatusBadge({ status }: { status: EventStatus }) {
  const tone =
    status === "FINISHED" || status === "REPORT_DELIVERED"
      ? "success"
      : status === "CANCELLED"
        ? "danger"
        : status === "IN_PROGRESS"
          ? "default"
          : "warning";

  return <Badge tone={tone}>{eventStatusLabels[status]}</Badge>;
}
