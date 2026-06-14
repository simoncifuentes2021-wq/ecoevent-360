import { RoleGuard } from "@/components/layout/RoleGuard";
import { WorkerOrdersPage } from "@/components/orders/WorkerOrdersPage";

export default function WorkerOrdersRoute() {
  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <WorkerOrdersPage />
    </RoleGuard>
  );
}
