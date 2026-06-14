import { OrderDetailPage } from "@/components/orders/OrderDetailPage";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function AdminOrderRoute({ params }: { params: { order_id: string } }) {
  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN", "SUPERVISOR"]}>
      <OrderDetailPage orderId={params.order_id} backHref="/admin/eventos" />
    </RoleGuard>
  );
}
