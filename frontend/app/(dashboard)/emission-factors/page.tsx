import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { source: "Diesel generador", unit: "litro", factor: "2.68 kg CO2e", status: "Vigente" },
  { source: "Transporte liviano", unit: "km", factor: "0.21 kg CO2e", status: "Vigente" },
  { source: "Residuo general", unit: "kg", factor: "0.42 kg CO2e", status: "Revision" }
];

export default function EmissionFactorsPage() {
  return (
    <CrudShell
      title="Factores de emision"
      description="Catalogo base para los calculos de CO2e."
      columns={[
        { key: "source", label: "Fuente" },
        { key: "unit", label: "Unidad" },
        { key: "factor", label: "Factor" },
        { key: "status", label: "Estado", badge: true }
      ]}
      rows={rows}
    />
  );
}

