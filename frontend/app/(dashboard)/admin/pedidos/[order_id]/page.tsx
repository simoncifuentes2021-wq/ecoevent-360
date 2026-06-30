import { redirect } from "next/navigation";

export default function AdminOrderDetailRedirectPage({ params }: { params: { order_id: string } }) {
  redirect(`/admin/logistica/pedidos/${params.order_id}`);
}
