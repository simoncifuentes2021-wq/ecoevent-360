import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { event: "Festival Puerto Verde", service: "Gestion residuos", quantity: "8 jornadas", status: "Activo" },
  { event: "Festival Puerto Verde", service: "Banos quimicos", quantity: "42 unidades", status: "Activo" },
  { event: "Expo Industria Circular", service: "Limpieza post evento", quantity: "3 jornadas", status: "Planificado" }
];

export default function ContractedServicesPage() {
  return (
    <CrudShell
      title="Servicios contratados"
      description="Servicios asignados a cada evento y sus cantidades."
      columns={[
        { key: "event", label: "Evento" },
        { key: "service", label: "Servicio" },
        { key: "quantity", label: "Cantidad" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}

