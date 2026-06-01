import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { name: "Arauco Live", contact: "Paula Rivas", email: "paula@araucolive.cl", status: "Activo" },
  { name: "Nodo Sur", contact: "Martin Soto", email: "martin@nodosur.cl", status: "Activo" },
  { name: "RunCo", contact: "Camila Vera", email: "camila@runco.cl", status: "Revision" }
];

export default function ClientsPage() {
  return (
    <CrudShell
      title="Clientes"
      description="Empresas contratantes y contactos responsables."
      columns={[
        { key: "name", label: "Cliente" },
        { key: "contact", label: "Contacto" },
        { key: "email", label: "Email" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}

