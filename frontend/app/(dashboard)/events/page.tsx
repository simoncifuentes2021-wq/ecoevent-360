import { CrudShell } from "@/components/forms/crud-shell";
import { events } from "@/lib/mock-data";

export default function EventsPage() {
  return (
    <CrudShell
      title="Eventos"
      description="Planificacion, estado y ubicacion de eventos."
      columns={[
        { key: "name", label: "Evento" },
        { key: "client", label: "Cliente" },
        { key: "city", label: "Ciudad" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={events}
    />
  );
}

