import { Badge } from "@/components/ui/badge";

export function StatusBadge({ status }: { status: string }) {
  const tone =
    status.includes("FINISHED") || status.includes("COMPLETED") || status.includes("ACTIVE")
      ? "success"
      : status.includes("CANCELLED") || status.includes("CLOSED")
        ? "danger"
        : "warning";
  return <Badge tone={tone}>{status.replaceAll("_", " ")}</Badge>;
}
