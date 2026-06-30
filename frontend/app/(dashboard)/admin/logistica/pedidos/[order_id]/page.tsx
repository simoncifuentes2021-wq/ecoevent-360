import { LogisticsOrderDetailView } from "@/components/logistics/LogisticsOrderDetailView";

export default function AdminLogisticsOrderDetailPage({ params }: { params: { order_id: string } }) {
  return (
    <LogisticsOrderDetailView
      backHref="/admin/eventos"
      orderId={params.order_id}
      roles={["SUPER_ADMIN", "ADMIN"]}
    />
  );
}
