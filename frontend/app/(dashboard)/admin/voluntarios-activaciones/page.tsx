import { RoleGuard } from "@/components/layout/RoleGuard";
import { VolunteersActivationsModule } from "@/components/volunteers/VolunteersActivationsModule";

export default function VolunteersActivationsPage() {
  return <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}><VolunteersActivationsModule /></RoleGuard>;
}
