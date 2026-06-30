import { LogisticsOrderDetailView } from "@/components/logistics/LogisticsOrderDetailView";

export default function LogisticsOrderDetailPage({ params }: { params: { order_id: string } }) {
  return (
    <LogisticsOrderDetailView
      backHref="/logistica/mis-pedidos"
      orderId={params.order_id}
      roles={["LOGISTICS_OPERATOR"]}
    />
  );
}
