import type { WasteChartItem, WasteSummary } from "@/types/waste";

function num(value: unknown) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toItems(value: unknown): WasteChartItem[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map((item) => ({
      name: String(item.name ?? item.label ?? item.type ?? item.destination ?? item.zone ?? "Sin dato"),
      value: num(item.value ?? item.kg ?? item.total_kg ?? item.weight_kg),
      kg: num(item.kg ?? item.value ?? item.total_kg ?? item.weight_kg),
      percentage: item.percentage === undefined ? undefined : num(item.percentage)
    }));
  }
  if (typeof value === "object") {
    return Object.entries(value as Record<string, unknown>).map(([name, kg]) => ({ name, value: num(kg), kg: num(kg) }));
  }
  return [];
}

export function normalizeWasteSummary(raw: unknown): WasteSummary {
  const data = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const total = num(data.total_kg ?? data.total_waste_kg);
  const recovered = num(data.recovered_kg ?? data.recovered_waste_kg);
  const landfill = num(data.landfill_kg ?? data.landfill_waste_kg);
  return {
    total_kg: total,
    recovered_kg: recovered,
    recycled_kg: num(data.recycled_kg),
    organic_kg: num(data.organic_kg),
    landfill_kg: landfill,
    recycling_rate: num(data.recycling_rate),
    recovery_rate: num(data.recovery_rate ?? data.recovery_percentage ?? (total ? (recovered / total) * 100 : 0)),
    records_count: num(data.records_count ?? data.count),
    by_type: toItems(data.by_type),
    by_destination: toItems(data.by_destination),
    by_zone: toItems(data.by_zone)
  };
}

export function formatKg(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 2 })} kg`;
}

export function formatPercentage(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 1 })}%`;
}
