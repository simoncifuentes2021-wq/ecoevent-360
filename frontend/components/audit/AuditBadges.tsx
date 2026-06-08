import { Badge } from "@/components/ui/badge";
import { formatAuditModule, formatAuditStatus } from "@/lib/audit/formatAuditLog";

export function AuditStatusBadge({ status }: { status: string }) {
  const tone = status === "SUCCESS" ? "success" : status === "FAILED" || status === "DENIED" ? "danger" : "warning";
  return <Badge tone={tone}>{formatAuditStatus(status)}</Badge>;
}

export function AuditModuleBadge({ module }: { module: string }) {
  return <Badge>{formatAuditModule(module)}</Badge>;
}
