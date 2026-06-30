import { RoleGuard } from "@/components/layout/RoleGuard";
import { WorkerOrderDetailPage } from "@/components/orders/WorkerOrderDetailPage";

export default function WorkerOrderDetailRoute({ params }: { params: { order_id: string } }) {
  return (
    <RoleGuard roles={["LOGISTICS_OPERATOR"]}>
      <WorkerOrderDetailPage orderId={params.order_id} />
    </RoleGuard>
  );
}
