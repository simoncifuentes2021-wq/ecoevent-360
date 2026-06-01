import { Badge } from "@/components/ui/badge";

export function StaffRoleBadge({ role }: { role?: string | null }) {
  return <Badge tone={role?.toUpperCase().includes("SUP") ? "warning" : "neutral"}>{role || "Equipo"}</Badge>;
}
