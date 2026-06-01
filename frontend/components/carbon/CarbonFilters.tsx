"use client";

import { FilterSelect } from "@/components/common/FilterSelect";
import { SearchInput } from "@/components/common/SearchInput";

export const carbonCategories = ["TRANSPORT", "ENERGY", "WASTE", "WATER", "MATERIALS", "FOOD", "ACCOMMODATION", "OTHER"].map((value) => ({ label: value.replaceAll("_", " "), value }));
export const carbonScopes = [{ label: "Alcance 1", value: "SCOPE_1" }, { label: "Alcance 2", value: "SCOPE_2" }, { label: "Alcance 3", value: "SCOPE_3" }];
export const units = ["L", "kWh", "m3", "kg", "km", "unit", "hour"];

export function CarbonFilters({ q, category, scope, onQChange, onCategoryChange, onScopeChange }: { q: string; category: string; scope: string; onQChange: (value: string) => void; onCategoryChange: (value: string) => void; onScopeChange: (value: string) => void }) {
  return <div className="grid gap-3 md:grid-cols-[1fr_200px_180px]"><SearchInput placeholder="Buscar fuente o notas..." value={q} onChange={onQChange} /><FilterSelect label="Categoria" value={category} onChange={onCategoryChange} options={[{ label: "Todas", value: "" }, ...carbonCategories]} /><FilterSelect label="Alcance" value={scope} onChange={onScopeChange} options={[{ label: "Todos", value: "" }, ...carbonScopes]} /></div>;
}
