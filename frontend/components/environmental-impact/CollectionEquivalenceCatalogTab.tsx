"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { ExternalLink, Pencil, Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { useToast } from "@/components/common/ToastProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getWasteCollectionEquivalences, createWasteCollectionEquivalence, updateWasteCollectionEquivalence } from "@/lib/api/environmental";
import { getWasteTypes } from "@/lib/api/wasteTypes";
import type { WasteCollectionEquivalence } from "@/types/environmental";
import type { WasteType } from "@/types/waste";

type Scope = { key: string; kind: "FAMILY_DAYS" | "MATERIAL_UNITS"; waste_type_id: string | null; waste_type_name: string; existing?: WasteCollectionEquivalence };
type Draft = { name: string; reference_kg: string; display_unit: string; source: string; source_url: string; year: number; is_active: boolean };
const emptyDraft = (scope: Scope): Draft => ({
  name: scope.kind === "FAMILY_DAYS" ? "Residuos de una familia de 4 personas" : scope.waste_type_name,
  reference_kg: scope.kind === "FAMILY_DAYS" ? "4.5" : "",
  display_unit: scope.kind === "FAMILY_DAYS" ? "días de residuos de una familia" : "",
  source: scope.kind === "FAMILY_DAYS" ? "Santiago Recicla / MMA, Hoja de Ruta de Economía Circular RM, dato SUBDERE 2024: 1.12 kg por persona al día. Referencia redondeada para una familia de 4 personas: 4.5 kg/día, 135 kg en 30 días y 1,642.5 kg en 365 días." : "",
  source_url: scope.kind === "FAMILY_DAYS" ? "https://santiagorecicla.mma.gob.cl/wp-content/uploads/2024/08/Hoja-de-Ruta-EC-RM-19ago.pdf" : "",
  year: scope.kind === "FAMILY_DAYS" ? 2024 : new Date().getFullYear(),
  is_active: false,
});
const fieldClass = "mt-1 h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100";

export function CollectionEquivalenceCatalogTab() {
  const [factors, setFactors] = useState<WasteCollectionEquivalence[]>([]);
  const [types, setTypes] = useState<WasteType[]>([]);
  const [scope, setScope] = useState<Scope | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [factorData, typeData] = await Promise.all([getWasteCollectionEquivalences(), getWasteTypes()]);
      setFactors(factorData);
      setTypes(typeData);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo cargar el catálogo de equivalencias de Acopios.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const familyFactor = useMemo(() => factors.find((factor) => factor.kind === "FAMILY_DAYS"), [factors]);
  const byType = useMemo(() => {
    const grouped = new Map<string, WasteCollectionEquivalence[]>();
    factors.filter((factor) => factor.kind === "MATERIAL_UNITS" && factor.waste_type_id).forEach((factor) => {
      const items = grouped.get(factor.waste_type_id!) ?? [];
      items.push(factor);
      grouped.set(factor.waste_type_id!, items);
    });
    return grouped;
  }, [factors]);

  function openEditor(nextScope: Scope, existing?: WasteCollectionEquivalence) {
    const key = existing?.key ?? (nextScope.kind === "FAMILY_DAYS"
      ? "FAMILY_DAILY_WASTE"
      : `MATERIAL_${nextScope.waste_type_id!.replaceAll("-", "_").toUpperCase()}_${Date.now()}_${Math.random().toString(36).slice(2, 7).toUpperCase()}`);
    const scopeWithExisting = { ...nextScope, key, existing };
    setScope(scopeWithExisting);
    setDraft(existing ? {
      name: existing.name,
      reference_kg: String(existing.reference_kg),
      display_unit: existing.display_unit,
      source: existing.source,
      source_url: existing.source_url || "",
      year: existing.year,
      is_active: existing.is_active,
    } : emptyDraft(scopeWithExisting));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!scope || !draft) return;
    setSaving(true);
    try {
      const data = {
        key: scope.key,
        kind: scope.kind,
        waste_type_id: scope.waste_type_id,
        name: draft.name.trim(),
        reference_kg: draft.reference_kg.trim(),
        display_unit: draft.display_unit.trim(),
        source: draft.source.trim(),
        source_url: draft.source_url.trim() || null,
        year: draft.year,
        is_active: draft.is_active,
      };
      if (scope.existing) await updateWasteCollectionEquivalence(scope.existing.id, data);
      else await createWasteCollectionEquivalence(data);
      setScope(null);
      setDraft(null);
      toast({ tone: "success", title: "Equivalencia guardada", description: "El dashboard usará este factor solo si está activo." });
      await load();
    } catch (reason) {
      toast({ tone: "error", title: "No se pudo guardar", description: reason instanceof Error ? reason.message : undefined });
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <LoadingState label="Cargando equivalencias de Acopios..." />;
  if (error && !factors.length && !types.length) return <ErrorState title="No se pudo cargar el catálogo" message={error} onRetry={load} />;

  const familyScope: Scope = { key: familyFactor?.key ?? "FAMILY_DAILY_WASTE", kind: "FAMILY_DAYS", waste_type_id: null, waste_type_name: "General" };
  return <div className="space-y-5">
    {error ? <ErrorState message={error} onRetry={load} /> : null}
    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-950">
      Configura aquí los factores que podrán aparecer en el dashboard de Acopios. Puedes añadir varias comparaciones para un mismo material. La fuente y el peso de referencia quedan en administración; el cliente solo verá el resultado y una nota de estimación potencial.
    </div>
    <section className="rounded-2xl border bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">Comparación general</p><h3 className="mt-1 text-lg font-bold">Residuos de una familia de 4 personas</h3><p className="mt-1 text-sm text-slate-600">Referencia acordada: 4,5 kg al día, 135 kg en 30 días y 1.642,5 kg en 365 días.</p></div><Button variant="secondary" onClick={() => openEditor(familyScope, familyFactor)}><Pencil className="h-4 w-4"/>{familyFactor ? "Editar factor" : "Configurar factor"}</Button></div>
      <FactorStatus item={familyFactor} />
    </section>
    <section className="space-y-3">
      <div><h3 className="text-lg font-bold">Equivalencias por material</h3><p className="text-sm text-slate-600">Agrega una o más comparaciones para cada material. Los materiales sin un factor confiable pueden quedar solo con sus kilos recibidos.</p></div>
      <div className="grid gap-3 lg:grid-cols-2">{types.map((type) => {
        const items = byType.get(type.id) ?? [];
        return <article className="rounded-2xl border bg-white p-4 shadow-sm" key={type.id}>
          <div className="flex flex-wrap items-center justify-between gap-3"><h4 className="font-semibold text-slate-900">{type.name}</h4><Button size="sm" variant="secondary" onClick={() => openEditor({ key: "", kind: "MATERIAL_UNITS", waste_type_id: type.id, waste_type_name: type.name })}><Plus className="h-4 w-4"/>Agregar equivalencia</Button></div>
          {items.length ? <ul className="mt-3 space-y-3">{items.map((item) => <li className="flex flex-wrap items-start justify-between gap-3 border-t border-slate-100 pt-3" key={item.id}><div><p className="text-sm font-medium text-slate-800">{item.name}</p><p className="mt-1 text-xs text-slate-500">{item.display_unit} · {Number(item.reference_kg).toLocaleString("es-CL")} kg por unidad</p><FactorStatus item={item}/></div><Button size="sm" variant="ghost" onClick={() => openEditor({ key: item.key, kind: "MATERIAL_UNITS", waste_type_id: type.id, waste_type_name: type.name }, item)}><Pencil className="h-4 w-4"/>Editar</Button></li>)}</ul> : <p className="mt-3 text-sm text-slate-500">Sin equivalencias configuradas.</p>}
        </article>;
      })}</div>
    </section>
    {scope && draft ? <ModalShell title={scope.existing ? "Editar equivalencia de Acopios" : "Agregar equivalencia de Acopios"} description="Los datos de referencia se guardan para revisión administrativa y no se muestran al cliente." onClose={() => { setScope(null); setDraft(null); }}>
      <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => void save(event)}>
        <label className="grid gap-1 text-sm sm:col-span-2">Nombre visible<Input required maxLength={180} value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })}/></label>
        <label className="grid gap-1 text-sm">Peso de referencia (kg)<Input required min="0.000001" step="any" type="number" value={draft.reference_kg} onChange={(event) => setDraft({ ...draft, reference_kg: event.target.value })}/><span className="text-xs text-slate-500">Kg del residuo para obtener una unidad del resultado mostrado. En la equivalencia familiar, kg generados por familia en un día.</span></label>
        <label className="grid gap-1 text-sm">Unidad que verá el cliente<Input required maxLength={120} placeholder={scope.kind === "FAMILY_DAYS" ? "días de residuos de una familia" : "kWh potenciales"} value={draft.display_unit} onChange={(event) => setDraft({ ...draft, display_unit: event.target.value })}/></label>
        <label className="grid gap-1 text-sm sm:col-span-2">Fuente y referencia interna<textarea required maxLength={2000} className={`${fieldClass} min-h-24 py-3`} value={draft.source} onChange={(event) => setDraft({ ...draft, source: event.target.value })}/></label>
        <label className="grid gap-1 text-sm sm:col-span-2">Enlace de la fuente (opcional)<Input type="url" value={draft.source_url} onChange={(event) => setDraft({ ...draft, source_url: event.target.value })}/></label>
        <label className="grid gap-1 text-sm">Año de referencia<Input required min="1900" max="2200" type="number" value={draft.year} onChange={(event) => setDraft({ ...draft, year: Number(event.target.value) })}/></label>
        <label className="flex items-center gap-2 self-end pb-3 text-sm"><input checked={draft.is_active} type="checkbox" onChange={(event) => setDraft({ ...draft, is_active: event.target.checked })}/>Mostrar en dashboard</label>
        <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={() => { setScope(null); setDraft(null); }}>Cancelar</Button><Button disabled={saving}>{saving ? "Guardando..." : "Guardar"}</Button></div>
      </form>
    </ModalShell> : null}
  </div>;
}

function FactorStatus({ item }: { item?: WasteCollectionEquivalence }) {
  if (!item) return <p className="mt-2 text-xs text-amber-700">Pendiente de configurar y validar.</p>;
  return <p className={`mt-2 inline-flex flex-wrap items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${item.is_active ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}`}>{item.is_active ? "Activo en el dashboard" : "Guardado · no visible al cliente"}{item.source_url ? <> · <a className="inline-flex items-center gap-1 underline" href={item.source_url} rel="noreferrer" target="_blank">Fuente {item.year}<ExternalLink className="h-3 w-3"/></a></> : ` · ${item.year}`}</p>;
}
