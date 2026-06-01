import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { name: "Gestion residuos", category: "Ambiental", unit: "kg", status: "Disponible" },
  { name: "Banos quimicos", category: "Sanitario", unit: "unidad", status: "Disponible" },
  { name: "Limpieza post evento", category: "Operacion", unit: "jornada", status: "Disponible" }
];

export default function ServicesPage() {
  return (
    <CrudShell
      title="Servicios"
      description="Catalogo y unidades comerciales."
      columns={[
        { key: "name", label: "Servicio" },
        { key: "category", label: "Categoria" },
        { key: "unit", label: "Unidad" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}

