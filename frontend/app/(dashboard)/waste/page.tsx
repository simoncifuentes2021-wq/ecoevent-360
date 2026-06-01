import { CrudShell } from "@/components/forms/crud-shell";

const rows = [
  { material: "PET", weight: "420 kg", destination: "Reciclaje", zone: "Acceso Norte" },
  { material: "Organico", weight: "920 kg", destination: "Compostaje", zone: "Patio Comidas" },
  { material: "General", weight: "680 kg", destination: "Disposicion", zone: "Backstage" }
];

export default function WastePage() {
  return (
    <CrudShell
      title="Residuos"
      description="Materiales, peso y destino final."
      columns={[
        { key: "material", label: "Material" },
        { key: "weight", label: "Peso" },
        { key: "destination", label: "Destino", badge: true },
        { key: "zone", label: "Zona" }
      ]}
      rows={rows}
    />
  );
}

