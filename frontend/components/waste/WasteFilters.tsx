"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";
import type { WasteType, WasteTypeCode } from "@/types/waste";
import type { Zone } from "@/types/zone";

export const fallbackWasteTypes: Array<{ label: string; value: WasteTypeCode }> = [
  { label: "Plastico", value: "PLASTIC" },
  { label: "Carton/Papel", value: "CARDBOARD" },
  { label: "Vidrio", value: "GLASS" },
  { label: "Aluminio", value: "ALUMINUM" },
  { label: "Organico", value: "ORGANIC" },
  { label: "General", value: "GENERAL" },
  { label: "Peligroso", value: "HAZARDOUS" },
  { label: "Otro", value: "OTHER" }
];

export const destinations = [
  { label: "Reciclaje", value: "RECYCLING" },
  { label: "Compostaje", value: "COMPOSTING" },
  { label: "Relleno sanitario", value: "LANDFILL" },
  { label: "Recuperacion", value: "RECOVERY" },
  { label: "Disposicion especial", value: "SPECIAL_DISPOSAL" },
  { label: "Otro", value: "OTHER" }
];

export function WasteFilters({ q, zoneId, typeId, destination, zones, wasteTypes, onQChange, onZoneChange, onTypeChange, onDestinationChange }: { q: string; zoneId: string; typeId: string; destination: string; zones: Zone[]; wasteTypes: WasteType[]; onQChange: (value: string) => void; onZoneChange: (value: string) => void; onTypeChange: (value: string) => void; onDestinationChange: (value: string) => void }) {
  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_180px_200px_200px]">
      <SearchInput placeholder="Buscar por detalle o notas..." value={q} onChange={onQChange} />
      <FilterSelect label="Zona" value={zoneId} onChange={onZoneChange} options={[{ label: "Todas", value: "" }, ...zones.map((zone) => ({ label: zone.name, value: zone.id }))]} />
      <FilterSelect label="Tipo" value={typeId} onChange={onTypeChange} options={[{ label: "Todos", value: "" }, ...(wasteTypes.length ? wasteTypes.map((type) => ({ label: type.name, value: type.id })) : fallbackWasteTypes)]} />
      <FilterSelect label="Destino" value={destination} onChange={onDestinationChange} options={[{ label: "Todos", value: "" }, ...destinations]} />
    </div>
  );
}
