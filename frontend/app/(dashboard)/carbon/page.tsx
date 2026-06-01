import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { source: "Transporte staff", quantity: "180 km", factor: "0.21", total: "37.8 kg CO2e" },
  { source: "Energia generador", quantity: "240 l", factor: "2.68", total: "643.2 kg CO2e" },
  { source: "Residuos general", quantity: "680 kg", factor: "0.42", total: "285.6 kg CO2e" }
];

export default function CarbonPage() {
  return (
    <CrudShell
      title="Huella de carbono"
      description="Fuentes, factores y totales CO2e."
      columns={[
        { key: "source", label: "Fuente" },
        { key: "quantity", label: "Cantidad" },
        { key: "factor", label: "Factor" },
        { key: "total", label: "Total" }
      ]}
      rows={rows}
    />
  );
}

