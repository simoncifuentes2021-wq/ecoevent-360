"use client";

import { ClientReportsPage } from "@/components/client/ClientReportsPage";
import { RoleGuard } from "@/components/layout/RoleGuard";

export default function ClientReportsRoute() {
  return (
    <RoleGuard roles={["CLIENT"]}>
      <div className="space-y-6">
        <div>
          <p className="text-sm font-semibold uppercase text-primary">Portal cliente</p>
          <h1 className="mt-1 text-3xl font-bold">Reportes</h1>
          <p className="mt-2 text-muted-foreground">Descarga informes finales disponibles para tus eventos.</p>
        </div>
        <ClientReportsPage />
      </div>
    </RoleGuard>
  );
}
