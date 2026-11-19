import { RoleGuard } from "@/components/layout/RoleGuard";
import { VolunteersActivationsModule } from "@/components/volunteers/VolunteersActivationsModule";

export default function LogisticsVolunteersActivationsPage() {
  return <RoleGuard roles={["LOGISTICS_OPERATOR"]}><VolunteersActivationsModule /></RoleGuard>;
}
