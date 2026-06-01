import { StatusBadge } from "@/components/common/StatusBadge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { Client } from "@/types/client";

export function ClientSummary({ client }: { client: Client }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <h2 className="font-semibold">Resumen del cliente</h2>
          <StatusBadge status={client.is_active ? "ACTIVE" : "INACTIVE"} />
        </div>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <Info label="Razón social" value={client.business_name} />
        <Info label="RUT" value={client.rut ?? "Sin RUT"} />
        <Info label="Contacto" value={client.contact_name ?? "Sin contacto"} />
        <Info label="Email" value={client.contact_email ?? "Sin email"} />
        <Info label="Teléfono" value={client.contact_phone ?? "Sin teléfono"} />
        <Info label="Industria" value={client.industry ?? "Sin industria"} />
        <Info label="Dirección" value={client.address ?? "Sin dirección"} />
        <Info label="Notas" value={client.notes ?? "Sin notas"} />
      </CardContent>
    </Card>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase text-muted-foreground">{label}</p>
      <p className="mt-1 font-medium">{value}</p>
    </div>
  );
}
