import { LogisticsOrderDetailView } from "@/components/logistics/LogisticsOrderDetailView";

export default function SupervisorLogisticsOrderDetailPage({ params }: { params: { order_id: string } }) {
  return (
    <LogisticsOrderDetailView
      backHref="/supervisor/eventos"
      orderId={params.order_id}
      roles={["SUPERVISOR"]}
    />
  );
}
