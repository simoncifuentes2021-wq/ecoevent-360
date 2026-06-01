import type { EnergyRecord, FuelRecord, WaterRecord } from "@/types/operations";

export function normalizeFuelRecords(raw: FuelRecord[] | { items?: FuelRecord[] }) {
  return Array.isArray(raw) ? raw : raw.items || [];
}

export function normalizeEnergyRecords(raw: EnergyRecord[] | { items?: EnergyRecord[] }) {
  return Array.isArray(raw) ? raw : raw.items || [];
}

export function normalizeWaterRecords(raw: WaterRecord[] | { items?: WaterRecord[] }) {
  return Array.isArray(raw) ? raw : raw.items || [];
}

export const formatLiters = (value: number) => `${Number(value || 0).toLocaleString("es-CL")} L`;
export const formatKwh = (value: number) => `${Number(value || 0).toLocaleString("es-CL")} kWh`;
export const formatM3 = (value: number) => `${Number(value || 0).toLocaleString("es-CL")} m3`;
