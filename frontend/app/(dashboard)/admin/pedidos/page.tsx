import { redirect } from "next/navigation";

export default function AdminOrdersRedirectPage() {
  redirect("/admin/logistica/pedidos");
}
