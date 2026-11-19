import { RoleGuard } from "@/components/layout/RoleGuard";
import { VolunteersActivationsModule } from "@/components/volunteers/VolunteersActivationsModule";

export default function WorkerVolunteersActivationsPage() {
  return <RoleGuard roles={["WORKER"]}><VolunteersActivationsModule /></RoleGuard>;
}
