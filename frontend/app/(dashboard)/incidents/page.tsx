import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { title: "Contenedor saturado", zone: "Patio Comidas", severity: "MEDIUM", status: "REPORTED" },
  { title: "Derrame menor", zone: "Backstage", severity: "HIGH", status: "REPORTED" },
  { title: "Falta de insumos", zone: "Zona VIP", severity: "LOW", status: "CLOSED" }
];

export default function IncidentsPage() {
  return (
    <CrudShell
      title="Incidencias"
      description="Registro, severidad y cierre de hallazgos."
      columns={[
        { key: "title", label: "Incidencia" },
        { key: "zone", label: "Zona" },
        { key: "severity", label: "Severidad", badge: true },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}
