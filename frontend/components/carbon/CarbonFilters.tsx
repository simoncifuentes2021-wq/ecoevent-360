"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export const carbonCategoryLabels: Record<string, string> = {
  TRANSPORT: "Transporte",
  ENERGY: "Energia",
  WASTE: "Residuos",
  WATER: "Agua",
  MATERIALS: "Materiales",
  FOOD: "Alimentacion",
  ACCOMMODATION: "Alojamiento",
  OTHER: "Otro"
};

const carbonCategoryAliases: Record<string, string> = {
  TRANSPORTE: "TRANSPORT",
  TRANSPORT: "TRANSPORT",
  ENERGY: "ENERGY",
  ENERGIA: "ENERGY",
  RESIDUOS: "WASTE",
  WASTE: "WASTE",
  AGUA: "WATER",
  WATER: "WATER",
  MATERIALES: "MATERIALS",
  MATERIALS: "MATERIALS",
  ALIMENTACION: "FOOD",
  FOOD: "FOOD",
  ALOJAMIENTO: "ACCOMMODATION",
  ACCOMMODATION: "ACCOMMODATION",
  OTRO: "OTHER",
  OTHER: "OTHER"
};

export function normalizeCarbonCategory(value?: string | null) {
  const key = String(value || "OTHER")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replaceAll("_", " ")
    .trim()
    .toUpperCase();
  return carbonCategoryAliases[key] || carbonCategoryAliases[key.replaceAll(" ", "_")] || key;
}

export function getCarbonCategoryLabel(value?: string | null) {
  const normalized = normalizeCarbonCategory(value);
  return carbonCategoryLabels[normalized] || value || carbonCategoryLabels.OTHER;
}

export const carbonCategories = Object.entries(carbonCategoryLabels).map(([value, label]) => ({ label, value }));
export const carbonScopes = [{ label: "Alcance 1", value: "SCOPE_1" }, { label: "Alcance 2", value: "SCOPE_2" }, { label: "Alcance 3", value: "SCOPE_3" }];
export const units = ["L", "kWh", "m3", "kg", "km", "unit", "hour"];

export function CarbonFilters({ q, category, scope, onQChange, onCategoryChange, onScopeChange }: { q: string; category: string; scope: string; onQChange: (value: string) => void; onCategoryChange: (value: string) => void; onScopeChange: (value: string) => void }) {
  return <div className="grid gap-3 md:grid-cols-[1fr_200px_180px]"><SearchInput placeholder="Buscar fuente o notas..." value={q} onChange={onQChange} /><FilterSelect label="Categoria" value={category} onChange={onCategoryChange} options={[{ label: "Todas", value: "" }, ...carbonCategories]} /><FilterSelect label="Alcance" value={scope} onChange={onScopeChange} options={[{ label: "Todos", value: "" }, ...carbonScopes]} /></div>;
}
