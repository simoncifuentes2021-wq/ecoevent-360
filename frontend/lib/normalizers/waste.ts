import type { WasteChartItem, WasteSummary } from "@/types/waste";

function num(value: unknown) {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function toItems(value: unknown): WasteChartItem[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value.map((item) => ({
      id: item.id == null ? null : String(item.id),
      waste_type_id: item.waste_type_id == null ? item.id == null ? null : String(item.id) : String(item.waste_type_id),
      collection_point_id: item.collection_point_id == null ? null : String(item.collection_point_id),
      code: item.code == null ? undefined : String(item.code),
      source: item.source == null ? undefined : String(item.source),
      name: String(item.name ?? item.label ?? item.type ?? item.destination ?? item.zone ?? "Sin dato"),
      value: num(item.value ?? item.kg ?? item.total_kg ?? item.weight_kg),
      kg: num(item.kg ?? item.value ?? item.total_kg ?? item.weight_kg),
      collection_points_kg: item.collection_points_kg === undefined ? undefined : num(item.collection_points_kg),
      direct_kg: item.direct_kg === undefined ? undefined : num(item.direct_kg),
      records_count: item.records_count === undefined ? undefined : num(item.records_count),
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
  const recovered = num(data.recovered_kg ?? data.recovered_waste_kg);
  const landfill = num(data.landfill_kg ?? data.landfill_waste_kg);
  const bySource = toItems(data.by_source);
  const collectionData = (data.collection_points && typeof data.collection_points === "object" ? data.collection_points : {}) as Record<string, unknown>;
  const directData = (data.direct_records && typeof data.direct_records === "object" ? data.direct_records : {}) as Record<string, unknown>;
  const byType = toItems(data.by_type);
  const byCollectionPoint = toItems(data.by_collection_point);
  const topWasteType = data.top_waste_type ? toItems([data.top_waste_type])[0] ?? null : byType[0] ?? null;
  const topCollectionPoint = data.top_collection_point ? toItems([data.top_collection_point])[0] ?? null : byCollectionPoint[0] ?? null;
  const total = num(data.total_event_kg ?? data.total_kg ?? data.total_waste_kg);
  const collectionSource = bySource.find((item) => item.source === "COLLECTION_POINT");
  const directSource = bySource.find((item) => item.source === "DIRECT");
  return {
    total_kg: total,
    total_event_kg: total,
    recovered_kg: recovered,
    special_disposal_kg: num(data.special_disposal_kg),
    recycled_kg: num(data.recycled_kg),
    organic_kg: num(data.organic_kg),
    landfill_kg: landfill,
    recycling_rate: num(data.recycling_rate),
    recovery_rate: num(data.recovery_rate ?? data.recovery_percentage ?? (total ? (recovered / total) * 100 : 0)),
    records_count: num(data.total_records ?? data.records_count ?? data.record_count ?? data.count),
    total_records: num(data.total_records ?? data.records_count ?? data.record_count ?? data.count),
    waste_types_count: num(data.waste_types_count),
    collection_points: {
      weight_kg: num(collectionData.weight_kg ?? collectionSource?.kg),
      percentage: num(collectionData.percentage ?? collectionSource?.percentage),
      records_count: num(collectionData.records_count)
    },
    direct_records: {
      weight_kg: num(directData.weight_kg ?? directSource?.kg),
      percentage: num(directData.percentage ?? directSource?.percentage),
      records_count: num(directData.records_count)
    },
    top_waste_type: topWasteType,
    top_collection_point: topCollectionPoint,
    by_source: bySource,
    by_collection_point: byCollectionPoint,
    by_type: byType,
    by_destination: toItems(data.by_destination),
    by_zone: toItems(data.by_zone)
  };
}

export function formatKg(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 2 })} kg`;
}

export function formatPercentage(value: number) {
  return `${Number(value || 0).toLocaleString("es-CL", { maximumFractionDigits: 1 })} %`;
}
