import { Badge } from "@/components/ui/badge";
import type { ReportStatus } from "@/types/report";

const labels: Record<ReportStatus, string> = {
  DRAFT: "Borrador",
  GENERATED: "Generado",
  DELIVERED: "Entregado",
  ARCHIVED: "Archivado",
  FAILED: "Fallido"
};

export function ReportStatusBadge({ status }: { status: ReportStatus | string }) {
  const tone = status === "DELIVERED" || status === "GENERATED" ? "success" : status === "FAILED" ? "danger" : status === "ARCHIVED" ? "neutral" : "warning";
  return <Badge tone={tone}>{labels[status as ReportStatus] ?? status}</Badge>;
}
