import { RoleGuard } from "@/components/layout/RoleGuard";
import { VolunteersActivationsModule } from "@/components/volunteers/VolunteersActivationsModule";

export default function SupervisorVolunteersActivationsPage() {
  return <RoleGuard roles={["SUPERVISOR"]}><VolunteersActivationsModule /></RoleGuard>;
}
