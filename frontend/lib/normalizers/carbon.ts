import type { CarbonChartItem, CarbonRecord, CarbonSummary } from "@/types/carbon";

function num(value: unknown) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function items(value: unknown): CarbonChartItem[] {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((item) => ({ name: String(item.name ?? item.category ?? item.scope ?? item.source ?? item.date ?? "Sin dato"), value: num(item.value ?? item.kg ?? item.kg_co2e ?? item.emissions_kgco2e), kg: num(item.kg ?? item.value ?? item.kg_co2e ?? item.emissions_kgco2e) }));
  if (typeof value === "object") return Object.entries(value as Record<string, unknown>).map(([name, kg]) => ({ name, value: num(kg), kg: num(kg) }));
  return [];
}

export function normalizeCarbonSummary(raw: unknown): CarbonSummary {
  const data = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const totalKg = num(data.total_kg_co2e ?? data.total_emissions_kg ?? data.total_kgco2e);
  return {
    total_kg_co2e: totalKg,
    total_ton_co2e: num(data.total_ton_co2e ?? data.total_emissions_ton ?? totalKg / 1000),
    kg_co2e_per_attendee: num(data.kg_co2e_per_attendee ?? data.per_attendee_kg),
    records_count: num(data.records_count ?? data.count),
    by_category: items(data.by_category ?? data.emissions_by_category),
    by_scope: items(data.by_scope ?? data.emissions_by_scope),
    by_source: items(data.by_source ?? data.emissions_by_source),
    by_date: items(data.by_date ?? data.emissions_by_date)
  };
}

export function normalizeCarbonRecords(raw: CarbonRecord[] | { items?: CarbonRecord[] }) {
  return Array.isArray(raw) ? raw : raw.items || [];
}

export function normalizeCarbonChartData(raw: unknown) {
  return items(raw);
}

export function formatKgCO2e(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 2 })} kgCO2e`;
}

export function formatTonCO2e(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 3 })} tCO2e`;
}

export function formatKgCO2ePerAttendee(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 2 })} kgCO2e/asistente`;
}

export function formatEmissionFactor(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 6 })}`;
}

export function getMainEmissionCategory(summary: CarbonSummary) {
  return [...summary.by_category].sort((a, b) => b.kg - a.kg)[0]?.name || "Sin datos";
}
