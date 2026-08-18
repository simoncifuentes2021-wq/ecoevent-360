"use client";

import { useCallback, useEffect, useState } from "react";
import { ExternalLink, Pencil, Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { PageHeader } from "@/components/common/PageHeader";
import { useToast } from "@/components/common/ToastProvider";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createEnvironmentalEquivalence,
  createEnvironmentalFactor,
  createEnvironmentalMethodology,
  getEnvironmentalEquivalences,
  getEnvironmentalFactors,
  getEnvironmentalMethodologies,
  updateEnvironmentalEquivalence,
  updateEnvironmentalFactor,
  updateEnvironmentalMethodology,
} from "@/lib/api/environmental";
import type {
  EcoEquivalence,
  EnvironmentalActionType,
  EnvironmentalFactor,
  EnvironmentalMethodology,
  EnvironmentalMetricKey,
} from "@/types/environmental";

const actionTypes: Array<[EnvironmentalActionType, string]> = [
  ["ELECTRIC_LIGHTING_TOWER", "Torre eléctrica"], ["ELECTRIC_MOTORCYCLE", "Moto eléctrica"],
  ["ELECTRIC_CART", "Carrito eléctrico"], ["SOLAR_ENERGY", "Energía solar"],
  ["ELECTRIC_VEHICLE", "Vehículo eléctrico"], ["BIKE_MOBILITY", "Bicicleta"],
  ["PUBLIC_TRANSPORT", "Transporte público"], ["OTHER", "Otra solución"],
];
const metricKeys: EnvironmentalMetricKey[] = ["CO2E_AVOIDED_KG", "FUEL_AVOIDED_L", "ENERGY_KWH", "PM25_AVOIDED_KG", "PM10_AVOIDED_KG", "NOX_AVOIDED_KG"];
const fieldClass = "h-11 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100";
const areaClass = `${fieldClass} min-h-24 py-3`;
type Section = "factors" | "methodologies" | "equivalences";

export default function EnvironmentalCatalogPage() {
  const [section, setSection] = useState<Section>("factors");
  const [factors, setFactors] = useState<EnvironmentalFactor[]>([]);
  const [methods, setMethods] = useState<EnvironmentalMethodology[]>([]);
  const [equivalences, setEquivalences] = useState<EcoEquivalence[]>([]);
  const [editing, setEditing] = useState<EnvironmentalFactor | EnvironmentalMethodology | EcoEquivalence | null | undefined>();
  const [loading, setLoading] = useState(true); const [saving, setSaving] = useState(false); const [error, setError] = useState<string | null>(null);
  const { toast } = useToast();
  const load = useCallback(async () => { setLoading(true); setError(null); try { const [f, m, e] = await Promise.all([getEnvironmentalFactors(), getEnvironmentalMethodologies(), getEnvironmentalEquivalences()]); setFactors(f); setMethods(m); setEquivalences(e); } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo cargar el catálogo ambiental."); } finally { setLoading(false); } }, []);
  useEffect(() => { void load(); }, [load]);
  async function saved(task: () => Promise<unknown>) { setSaving(true); try { await task(); setEditing(undefined); toast({ tone: "success", title: "Configuración guardada", description: "El catálogo ambiental quedó actualizado y auditado." }); await load(); } catch (reason) { toast({ tone: "error", title: "No se pudo guardar", description: reason instanceof Error ? reason.message : undefined }); } finally { setSaving(false); } }
  const counts = { factors: factors.length, methodologies: methods.length, equivalences: equivalences.length };
  return <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}><div className="space-y-6">
    <PageHeader eyebrow="Administración" title="Configuración de impacto ambiental" description="Gobierna factores, comparaciones y equivalencias sin modificar la huella de carbono." actions={<Button onClick={() => setEditing(null)}><Plus className="h-4 w-4" />Crear {section === "factors" ? "factor" : section === "methodologies" ? "metodología" : "equivalencia"}</Button>} />
    <div className="flex gap-2 overflow-x-auto">{([ ["factors", "Factores"], ["methodologies", "Metodologías"], ["equivalences", "Equivalencias"] ] as const).map(([key, label]) => <Button key={key} variant={section === key ? "primary" : "secondary"} onClick={() => { setSection(key); setEditing(undefined); }}>{label} ({counts[key]})</Button>)}</div>
    {loading ? <LoadingState label="Cargando configuración ambiental..." /> : null}{error ? <ErrorState message={error} onRetry={load} /> : null}
    {!loading && !error && section === "factors" ? <FactorTable items={factors} onEdit={setEditing} /> : null}
    {!loading && !error && section === "methodologies" ? <MethodologyTable items={methods} onEdit={setEditing} /> : null}
    {!loading && !error && section === "equivalences" ? <EquivalenceTable items={equivalences} onEdit={setEditing} /> : null}
    {editing !== undefined && section === "factors" ? <FactorForm item={editing as EnvironmentalFactor | null} saving={saving} onClose={() => setEditing(undefined)} onSave={(data) => saved(() => editing ? updateEnvironmentalFactor(editing.id, data) : createEnvironmentalFactor(data as never))} /> : null}
    {editing !== undefined && section === "methodologies" ? <MethodologyForm item={editing as EnvironmentalMethodology | null} saving={saving} onClose={() => setEditing(undefined)} onSave={(data) => saved(() => editing ? updateEnvironmentalMethodology(editing.id, data) : createEnvironmentalMethodology(data as never))} /> : null}
    {editing !== undefined && section === "equivalences" ? <EquivalenceForm item={editing as EcoEquivalence | null} saving={saving} onClose={() => setEditing(undefined)} onSave={(data) => saved(() => editing ? updateEnvironmentalEquivalence(editing.id, data) : createEnvironmentalEquivalence(data as never))} /> : null}
  </div></RoleGuard>;
}

function Status({ active }: { active: boolean }) { return <span className={`rounded-full px-2 py-1 text-xs font-semibold ${active ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-500"}`}>{active ? "Activo" : "Inactivo"}</span>; }
function EditButton({ onClick }: { onClick: () => void }) { return <Button aria-label="Editar" size="sm" variant="ghost" onClick={onClick}><Pencil className="h-4 w-4" /></Button>; }

function FactorTable({ items, onEdit }: { items: EnvironmentalFactor[]; onEdit: (item: EnvironmentalFactor) => void }) { return <div className="overflow-x-auto rounded-xl border bg-white"><table className="w-full min-w-[1000px] text-sm"><thead className="bg-slate-50 text-left"><tr>{["Impacto", "Tecnología", "Base", "Factor", "Fuente", "Vigencia", ""].map((h) => <th className="p-3" key={h}>{h}</th>)}</tr></thead><tbody>{items.map((item) => <tr className="border-t" key={item.id}><td className="p-3 font-semibold">{item.impact_type}</td><td className="p-3">{item.technology}<p className="text-xs text-slate-500">{item.country || "Sin país"}</p></td><td className="p-3">{item.unit_basis}</td><td className="p-3 font-mono">{item.factor_value} {item.factor_unit}</td><td className="max-w-xs p-3"><span className="line-clamp-2">{item.source}</span>{item.source_url ? <a className="mt-1 inline-flex items-center gap-1 text-xs text-emerald-700" href={item.source_url} rel="noreferrer" target="_blank">Abrir fuente <ExternalLink className="h-3 w-3" /></a> : null}</td><td className="p-3"><Status active={item.is_active} /><p className="mt-1 text-xs text-slate-500">{item.year}</p></td><td className="p-3"><EditButton onClick={() => onEdit(item)} /></td></tr>)}</tbody></table></div>; }
function MethodologyTable({ items, onEdit }: { items: EnvironmentalMethodology[]; onEdit: (item: EnvironmentalMethodology) => void }) { return <div className="grid gap-3 lg:grid-cols-2">{items.map((item) => <article className="rounded-xl border bg-white p-5" key={item.id}><div className="flex items-start justify-between gap-3"><div><p className="font-bold">{item.name}</p><p className="mt-1 text-xs text-slate-500">{item.action_type}</p></div><div className="flex items-center gap-2"><Status active={item.is_active} /><EditButton onClick={() => onEdit(item)} /></div></div><div className="mt-4 grid grid-cols-2 gap-3 text-sm"><div className="rounded-lg bg-amber-50 p-3"><b>Línea base</b><p>{item.baseline_technology}</p></div><div className="rounded-lg bg-emerald-50 p-3"><b>Solución real</b><p>{item.actual_technology}</p></div></div><p className="mt-3 text-sm text-slate-600">{item.description}</p></article>)}</div>; }
function EquivalenceTable({ items, onEdit }: { items: EcoEquivalence[]; onEdit: (item: EcoEquivalence) => void }) { return <div className="overflow-x-auto rounded-xl border bg-white"><table className="w-full min-w-[800px] text-sm"><thead className="bg-slate-50 text-left"><tr>{["Equivalencia", "Métrica origen", "Conversión", "Fuente", "Estado", ""].map((h) => <th className="p-3" key={h}>{h}</th>)}</tr></thead><tbody>{items.map((item) => <tr className="border-t" key={item.id}><td className="p-3"><b>{item.name}</b><p className="text-xs text-slate-500">{item.key}</p></td><td className="p-3">{item.metric_source}</td><td className="p-3 font-mono">{item.factor} {item.unit}</td><td className="max-w-sm p-3">{item.source}<p className="text-xs text-slate-500">{item.year}</p></td><td className="p-3"><Status active={item.is_active} /></td><td className="p-3"><EditButton onClick={() => onEdit(item)} /></td></tr>)}</tbody></table></div>; }

function FactorForm({ item, saving, onClose, onSave }: FormProps<EnvironmentalFactor>) {
  const [value, setValue] = useState({ impact_type: item?.impact_type || "CO2E", technology: item?.technology || "", pollutant: item?.pollutant || "", unit_basis: item?.unit_basis || "ENERGY_KWH", factor_value: item?.factor_value || "0", factor_unit: item?.factor_unit || "kgCO2e/kWh", source: item?.source || "", source_url: item?.source_url || "", year: item?.year || new Date().getFullYear(), country: item?.country || "Chile", methodology: item?.methodology || "", is_active: item?.is_active ?? true });
  return <ModalShell title={item ? "Editar factor ambiental" : "Crear factor ambiental"} description={item ? "La identidad y unidad permanecen bloqueadas para conservar la trazabilidad histórica." : "Registra únicamente factores con fuente y metodología documentadas."} onClose={onClose} size="lg"><form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); void onSave(item ? { factor_value: value.factor_value, source: value.source, methodology: value.methodology, is_active: value.is_active } : { ...value, pollutant: value.pollutant || null, source_url: value.source_url || null, country: value.country || null }); }}>{[["impact_type", "Impacto"], ["technology", "Tecnología"], ["unit_basis", "Base de actividad"], ["factor_value", "Valor"], ["factor_unit", "Unidad del factor"], ["country", "País"], ["year", "Año"]].map(([key, label]) => <label className="grid gap-1 text-sm" key={key}>{label}<Input disabled={Boolean(item) && !["factor_value"].includes(key)} required value={String(value[key as keyof typeof value])} type={key === "year" || key === "factor_value" ? "number" : "text"} step="any" onChange={(e) => setValue({ ...value, [key]: key === "year" ? Number(e.target.value) : e.target.value })} /></label>)}<label className="grid gap-1 text-sm">Contaminante<Input disabled={Boolean(item)} value={value.pollutant} onChange={(e) => setValue({ ...value, pollutant: e.target.value })} /></label><label className="grid gap-1 text-sm sm:col-span-2">Fuente<textarea className={areaClass} required value={value.source} onChange={(e) => setValue({ ...value, source: e.target.value })} /></label><label className="grid gap-1 text-sm sm:col-span-2">URL de la fuente<Input disabled={Boolean(item)} type="url" value={value.source_url} onChange={(e) => setValue({ ...value, source_url: e.target.value })} /></label><label className="grid gap-1 text-sm sm:col-span-2">Metodología<textarea className={areaClass} required value={value.methodology} onChange={(e) => setValue({ ...value, methodology: e.target.value })} /></label>{item ? <Active value={value.is_active} onChange={(is_active) => setValue({ ...value, is_active })} /> : null}<Actions saving={saving} onClose={onClose} /></form></ModalShell>;
}

function MethodologyForm({ item, saving, onClose, onSave }: FormProps<EnvironmentalMethodology>) {
  const [value, setValue] = useState({ name: item?.name || "", action_type: item?.action_type || "ELECTRIC_LIGHTING_TOWER" as EnvironmentalActionType, baseline_technology: item?.baseline_technology || "", actual_technology: item?.actual_technology || "", description: item?.description || "", parameters: JSON.stringify(item?.parameters || { metrics: {} }, null, 2), is_active: item?.is_active ?? true }); const [jsonError, setJsonError] = useState("");
  return <ModalShell title={item ? "Editar metodología" : "Crear metodología"} description="La configuración avanzada referencia factores por ID y define las bases de actividad." onClose={onClose} size="lg"><form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); try { const parameters = JSON.parse(value.parameters) as Record<string, unknown>; setJsonError(""); void onSave(item ? { name: value.name, description: value.description, parameters, is_active: value.is_active } : { ...value, parameters }); } catch { setJsonError("La configuración JSON no es válida."); } }}><label className="grid gap-1 text-sm sm:col-span-2">Nombre<Input required value={value.name} onChange={(e) => setValue({ ...value, name: e.target.value })} /></label><label className="grid gap-1 text-sm">Tipo de acción<select className={fieldClass} disabled={Boolean(item)} value={value.action_type} onChange={(e) => setValue({ ...value, action_type: e.target.value as EnvironmentalActionType })}>{actionTypes.map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><span /><label className="grid gap-1 text-sm">Tecnología base<Input disabled={Boolean(item)} required value={value.baseline_technology} onChange={(e) => setValue({ ...value, baseline_technology: e.target.value })} /></label><label className="grid gap-1 text-sm">Tecnología real<Input disabled={Boolean(item)} required value={value.actual_technology} onChange={(e) => setValue({ ...value, actual_technology: e.target.value })} /></label><label className="grid gap-1 text-sm sm:col-span-2">Descripción<textarea className={areaClass} required value={value.description} onChange={(e) => setValue({ ...value, description: e.target.value })} /></label><label className="grid gap-1 text-sm sm:col-span-2">Configuración avanzada (JSON)<textarea className={`${areaClass} min-h-64 font-mono text-xs`} required value={value.parameters} onChange={(e) => setValue({ ...value, parameters: e.target.value })} />{jsonError ? <span className="text-xs text-rose-600">{jsonError}</span> : null}</label>{item ? <Active value={value.is_active} onChange={(is_active) => setValue({ ...value, is_active })} /> : null}<Actions saving={saving} onClose={onClose} /></form></ModalShell>;
}

function EquivalenceForm({ item, saving, onClose, onSave }: FormProps<EcoEquivalence>) {
  const [value, setValue] = useState({ key: item?.key || "", name: item?.name || "", metric_source: item?.metric_source || "CO2E_AVOIDED_KG" as EnvironmentalMetricKey, factor: item?.factor || "0", unit: item?.unit || "", source: item?.source || "", year: item?.year || new Date().getFullYear(), is_active: item?.is_active ?? true });
  return <ModalShell title={item ? "Editar equivalencia" : "Crear equivalencia"} description="Las equivalencias son comunicación contextual; no constituyen compensaciones." onClose={onClose}><form className="grid gap-4 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); void onSave(item ? { name: value.name, factor: value.factor, unit: value.unit, source: value.source, year: value.year, is_active: value.is_active } : value); }}><label className="grid gap-1 text-sm">Clave<Input disabled={Boolean(item)} pattern="[A-Z0-9_]+" required value={value.key} onChange={(e) => setValue({ ...value, key: e.target.value.toUpperCase() })} /></label><label className="grid gap-1 text-sm">Métrica origen<select className={fieldClass} disabled={Boolean(item)} value={value.metric_source} onChange={(e) => setValue({ ...value, metric_source: e.target.value as EnvironmentalMetricKey })}>{metricKeys.map((key) => <option key={key}>{key}</option>)}</select></label><label className="grid gap-1 text-sm sm:col-span-2">Nombre<Input required value={value.name} onChange={(e) => setValue({ ...value, name: e.target.value })} /></label><label className="grid gap-1 text-sm">Factor<Input min="0" required step="any" type="number" value={value.factor} onChange={(e) => setValue({ ...value, factor: e.target.value })} /></label><label className="grid gap-1 text-sm">Unidad<Input required value={value.unit} onChange={(e) => setValue({ ...value, unit: e.target.value })} /></label><label className="grid gap-1 text-sm sm:col-span-2">Fuente<textarea className={areaClass} required value={value.source} onChange={(e) => setValue({ ...value, source: e.target.value })} /></label><label className="grid gap-1 text-sm">Año<Input min="1900" required type="number" value={value.year} onChange={(e) => setValue({ ...value, year: Number(e.target.value) })} /></label>{item ? <Active value={value.is_active} onChange={(is_active) => setValue({ ...value, is_active })} /> : null}<Actions saving={saving} onClose={onClose} /></form></ModalShell>;
}

type FormProps<T> = { item: T | null; saving: boolean; onClose: () => void; onSave: (data: Record<string, unknown>) => Promise<void> };
function Active({ value, onChange }: { value: boolean; onChange: (value: boolean) => void }) { return <label className="flex items-center gap-2 text-sm"><input checked={value} type="checkbox" onChange={(e) => onChange(e.target.checked)} />Registro activo</label>; }
function Actions({ saving, onClose }: { saving: boolean; onClose: () => void }) { return <div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={saving}>{saving ? "Guardando..." : "Guardar"}</Button></div>; }
