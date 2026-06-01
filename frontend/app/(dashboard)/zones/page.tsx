import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { name: "Acceso Norte", event: "Festival Puerto Verde", owner: "Equipo A", status: "Activa" },
  { name: "Patio Comidas", event: "Festival Puerto Verde", owner: "Equipo B", status: "Activa" },
  { name: "Backstage", event: "Festival Puerto Verde", owner: "Equipo C", status: "Activa" }
];

export default function ZonesPage() {
  return (
    <CrudShell
      title="Zonas"
      description="Segmentacion operativa del recinto."
      columns={[
        { key: "name", label: "Zona" },
        { key: "event", label: "Evento" },
        { key: "owner", label: "Responsable" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}

