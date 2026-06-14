import { CatalogItemsPage } from "@/components/orders/CatalogItemsPage";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function CatalogItemsRoute() {
  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <CatalogItemsPage />
    </RoleGuard>
  );
}
