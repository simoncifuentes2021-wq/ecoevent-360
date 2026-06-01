import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { caption: "Punto limpio instalado", event: "Festival Puerto Verde", linked: "Tarea", status: "Validada" },
  { caption: "Contenedor saturado", event: "Festival Puerto Verde", linked: "Incidencia", status: "Pendiente" },
  { caption: "Retiro reciclables", event: "Maraton Costera", linked: "Residuo", status: "Validada" }
];

export default function EvidencesPage() {
  return (
    <CrudShell
      title="Evidencias fotograficas"
      description="Registro visual asociado a tareas, incidencias y residuos."
      columns={[
        { key: "caption", label: "Evidencia" },
        { key: "event", label: "Evento" },
        { key: "linked", label: "Asociada a", badge: true },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}

