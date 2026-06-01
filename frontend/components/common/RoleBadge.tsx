import { Badge } from "@/components/ui/badge";
import type { UserRole } from "@/types/roles";

const labels: Record<UserRole, string> = {
  SUPER_ADMIN: "Super admin",
  ADMIN: "Admin",
  CLIENT: "Cliente",
  SUPERVISOR: "Supervisor",
  WORKER: "Trabajador"
};

export function RoleBadge({ role }: { role: UserRole }) {
  const tone = role === "CLIENT" ? "warning" : role === "WORKER" ? "neutral" : "success";
  return <Badge tone={tone}>{labels[role]}</Badge>;
}
