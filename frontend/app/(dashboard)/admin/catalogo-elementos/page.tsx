import { redirect } from "next/navigation";

export default function CatalogItemsRedirectPage() {
  redirect("/admin/stock/productos");
}
