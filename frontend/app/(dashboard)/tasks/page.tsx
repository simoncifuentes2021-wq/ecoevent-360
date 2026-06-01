import { CrudShell } from "@/components/forms/crud-shell";
import { tasks } from "@/lib/mock-data";

export default function TasksPage() {
  return (
    <CrudShell
      title="Tareas operativas"
      description="Asignacion y seguimiento del equipo en terreno."
      columns={[
        { key: "title", label: "Tarea" },
        { key: "zone", label: "Zona" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={tasks}
    />
  );
}

