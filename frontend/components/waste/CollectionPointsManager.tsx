"use client";

import { useCallback, useEffect, useState } from "react";
import { Copy, MapPin, Plus, QrCode, Save, Search, X } from "lucide-react";
import { createCollectionPoint, getCollectionPoints, getEventWastePublicForm, getWasteCollectionRecords, getWasteCollectionSummary, updateCollectionPoint, updateEventWastePublicForm } from "@/lib/api/waste";
import { getEventZones } from "@/lib/api/zones";
import { getWasteTypes } from "@/lib/api/wasteTypes";
import type { EventWastePublicForm, WasteCollectionPoint, WasteCollectionRecord, WasteCollectionSummary, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";
import { Button } from "@/components/ui/button";

type Draft = { code: string; name: string; zone_id: string; location_description: string; capacity_kg: string; allowed_waste_type_ids: string[] };
const emptyDraft: Draft = { code: "", name: "", zone_id: "", location_description: "", capacity_kg: "", allowed_waste_type_ids: [] };
const dateLabel = (value: string) => new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", dateStyle: "short", timeStyle: "short" }).format(new Date(value));

export function CollectionPointsManager({ eventId, canManage }: { eventId: string; canManage: boolean }) {
  const [points, setPoints] = useState<WasteCollectionPoint[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [types, setTypes] = useState<WasteType[]>([]);
  const [summary, setSummary] = useState<WasteCollectionSummary | null>(null);
  const [records, setRecords] = useState<WasteCollectionRecord[]>([]);
  const [publicForm, setPublicForm] = useState<EventWastePublicForm | null>(null);
  const [formQrOpen, setFormQrOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pointFilter, setPointFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  const load = useCallback(async () => {
    try {
      const [items, zoneItems, wasteTypes, collectionSummary, form] = await Promise.all([
        getCollectionPoints(eventId), getEventZones(eventId), getWasteTypes().catch(() => []),
        getWasteCollectionSummary(eventId), getEventWastePublicForm(eventId),
      ]);
      setPoints(items); setZones(zoneItems); setTypes(wasteTypes); setSummary(collectionSummary); setPublicForm(form);
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudieron cargar los acopios."); }
  }, [eventId]);
  const loadRecords = useCallback(async () => {
    try {
      const result = await getWasteCollectionRecords(eventId, {
        collection_point_id: pointFilter || undefined,
        waste_type_id: typeFilter || undefined,
        search: search.trim() || undefined,
        date_from: dateFrom ? new Date(`${dateFrom}T00:00:00`).toISOString() : undefined,
        date_to: dateTo ? new Date(`${dateTo}T23:59:59.999`).toISOString() : undefined,
        page: 1, limit: 100,
      });
      setRecords(result.items);
    } catch (err) { setError(err instanceof Error ? err.message : "No se pudieron cargar los registros de acopio."); }
  }, [dateFrom, dateTo, eventId, pointFilter, search, typeFilter]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { void loadRecords(); }, [loadRecords]);

  function edit(point?: WasteCollectionPoint) {
    setEditing(point?.id || "new");
    setDraft(point ? { code: point.code, name: point.name, zone_id: point.zone_id || "", location_description: point.location_description || "", capacity_kg: point.capacity_kg == null ? "" : String(point.capacity_kg), allowed_waste_type_ids: point.allowed_waste_types.map(item => item.id) } : emptyDraft);
  }
  async function save() {
    setBusy(true); setError("");
    const body = { code: draft.code.trim(), name: draft.name.trim(), zone_id: draft.zone_id || null, location_description: draft.location_description || null, capacity_kg: draft.capacity_kg ? Number(draft.capacity_kg) : null, allowed_waste_type_ids: draft.allowed_waste_type_ids };
    try { if (editing === "new") await createCollectionPoint(eventId, body); else if (editing) await updateCollectionPoint(editing, body); setEditing(null); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo guardar el acopio."); }
    finally { setBusy(false); }
  }
  async function toggle(point: WasteCollectionPoint) {
    try { await updateCollectionPoint(point.id, { is_active: !point.is_active }); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo actualizar el acopio."); }
  }
  async function changePublicForm(action: "activate" | "close" | "regenerate-token") {
    try { setPublicForm(await updateEventWastePublicForm(eventId, action)); }
    catch (err) { setError(err instanceof Error ? err.message : "No se pudo actualizar el formulario público."); }
  }

  return <section className="space-y-5">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><h3 className="text-lg font-bold text-slate-900">Acopios Greenway</h3><p className="text-sm text-slate-600">Recepción de materiales separada de la gestión ambiental.</p></div>{canManage && !editing ? <Button onClick={() => edit()}><Plus className="h-4 w-4"/>Nuevo acopio</Button> : null}</div>
    {error ? <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
    {publicForm ? <section className="space-y-3 rounded-xl border border-emerald-200 bg-white p-4"><div className="flex flex-wrap items-start justify-between gap-3"><div><h4 className="font-bold">Formulario público Greenway</h4><p className="mt-1 text-sm"><b>Estado:</b> <span className={publicForm.status === "ACTIVE" ? "text-emerald-700" : "text-slate-600"}>{publicForm.status === "ACTIVE" ? "🟢 Público" : "⚫ Privado"}</span></p>{publicForm.public_url ? <a className="mt-1 block break-all text-sm text-emerald-800 underline" href={publicForm.public_url} target="_blank" rel="noreferrer">{publicForm.public_url}</a> : null}</div><div className="flex flex-wrap gap-2">{canManage ? publicForm.status === "ACTIVE" ? <Button variant="secondary" onClick={() => void changePublicForm("close")}>Cerrar formulario</Button> : <Button onClick={() => void changePublicForm("activate")}>Hacer público</Button> : null}<Button variant="secondary" onClick={() => setFormQrOpen(true)}><QrCode className="h-4 w-4"/>Ver QR</Button>{publicForm.public_url ? <Button variant="secondary" onClick={() => void navigator.clipboard.writeText(publicForm.public_url!)}><Copy className="h-4 w-4"/>Copiar enlace</Button> : null}{canManage ? <Button variant="secondary" onClick={() => void changePublicForm("regenerate-token")}>Regenerar enlace</Button> : null}</div></div></section> : null}
    {summary ? <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[["Total recibido", `${Number(summary.total_kg).toLocaleString("es-CL")} kg`], ["Registros", summary.records_count], ["Acopios activos", summary.active_points], ["Personas", summary.unique_submitters]].map(([label, value]) => <article className="rounded-xl border bg-white p-4" key={label}><p className="text-sm text-slate-500">{label}</p><p className="mt-1 text-2xl font-bold text-slate-950">{value}</p></article>)}
    </div> : null}
    {summary?.by_type.length ? <div className="grid gap-4 lg:grid-cols-2">
      {[{ title: "Kg por material", rows: summary.by_type.map(item => ({ key: item.id, label: item.name, kg: Number(item.total_kg) })) }, { title: "Kg por acopio", rows: summary.by_point.map(item => ({ key: item.id, label: `${item.code} · ${item.name}`, kg: Number(item.total_kg) })) }].map(chart => { const max = Math.max(...chart.rows.map(row => row.kg), 1); return <section className="rounded-xl border bg-white p-4" key={chart.title}><h4 className="font-bold">{chart.title}</h4><div className="mt-3 space-y-3">{chart.rows.map(row => <div key={row.key}><div className="mb-1 flex justify-between gap-3 text-sm"><span className="truncate">{row.label}</span><span className="shrink-0 font-semibold">{row.kg.toLocaleString("es-CL")} kg</span></div><div className="h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-emerald-600" style={{ width: `${Math.max(row.kg > 0 ? 2 : 0, row.kg / max * 100)}%` }}/></div></div>)}</div></section>; })}
    </div> : null}
    {editing ? <div className="grid gap-3 rounded-xl border bg-white p-4 sm:grid-cols-2">
      <label className="text-sm font-semibold">Código<input className="mt-1 w-full rounded-lg border p-3" value={draft.code} maxLength={40} onChange={e => setDraft({ ...draft, code: e.target.value })}/></label>
      <label className="text-sm font-semibold">Nombre<input className="mt-1 w-full rounded-lg border p-3" value={draft.name} maxLength={160} onChange={e => setDraft({ ...draft, name: e.target.value })}/></label>
      <label className="text-sm font-semibold">Zona<select className="mt-1 w-full rounded-lg border bg-white p-3" value={draft.zone_id} onChange={e => setDraft({ ...draft, zone_id: e.target.value })}><option value="">Sin zona</option>{zones.map(zone => <option key={zone.id} value={zone.id}>{zone.name}</option>)}</select></label>
      <label className="text-sm font-semibold">Capacidad (kg)<input type="number" min="0" step="0.1" className="mt-1 w-full rounded-lg border p-3" value={draft.capacity_kg} onChange={e => setDraft({ ...draft, capacity_kg: e.target.value })}/></label>
      <label className="text-sm font-semibold sm:col-span-2">Ubicación<input className="mt-1 w-full rounded-lg border p-3" value={draft.location_description} onChange={e => setDraft({ ...draft, location_description: e.target.value })}/></label>
      <fieldset className="space-y-2 sm:col-span-2"><legend className="text-sm font-semibold">Materiales permitidos</legend><div className="grid gap-2 sm:grid-cols-2">{types.map(type => <label key={type.id} className="flex items-center gap-2 rounded-lg border p-2 text-sm"><input type="checkbox" checked={draft.allowed_waste_type_ids.includes(type.id)} onChange={event => setDraft({ ...draft, allowed_waste_type_ids: event.target.checked ? [...draft.allowed_waste_type_ids, type.id] : draft.allowed_waste_type_ids.filter(id => id !== type.id) })}/>{type.name}</label>)}</div>{!types.length ? <p className="text-sm text-slate-500">No hay tipos de residuos disponibles en el catálogo.</p> : null}</fieldset>
      <div className="flex gap-2 sm:col-span-2"><Button disabled={busy || !draft.code.trim() || !draft.name.trim()} onClick={() => void save()}><Save className="h-4 w-4"/>Guardar</Button><Button variant="secondary" onClick={() => setEditing(null)}><X className="h-4 w-4"/>Cancelar</Button></div>
    </div> : null}
    {points.length ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{points.map(point => { const cap = Number(point.capacity_kg || 0); const kg = Number(point.total_kg || 0); const pct = cap > 0 ? Math.round(kg / cap * 100) : 0; return <article key={point.id} className={`rounded-xl border bg-white p-4 ${point.is_active ? "border-slate-200" : "border-slate-200 opacity-60"}`}>
      <div className="flex items-start justify-between gap-2"><div><span className="text-xs font-bold tracking-wider text-emerald-800">{point.code}</span><h4 className="mt-1 text-lg font-bold text-slate-950">{point.name}</h4></div><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${point.is_active ? "bg-emerald-100 text-emerald-800" : "bg-slate-100"}`}>{point.is_active ? "Activo" : "Inactivo"}</span></div>
      {point.location_description ? <p className="mt-2 flex gap-1.5 text-sm text-slate-600"><MapPin className="h-4 w-4 shrink-0"/>{point.location_description}</p> : null}
      <p className="mt-4 font-semibold text-slate-900">{kg.toLocaleString("es-CL")} kg recibidos{cap ? ` · ${cap.toLocaleString("es-CL")} kg capacidad` : ""}</p>{cap ? <div className="mt-2 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-emerald-600" style={{ width: `${Math.min(100, pct)}%` }}/></div> : null}<p className="mt-2 text-sm text-slate-500">{point.record_count} registros{cap ? ` · ${pct}% de capacidad` : ""}</p><p className="mt-2 text-sm text-slate-600">Materiales: {point.allowed_waste_types.length ? point.allowed_waste_types.map(item => item.name).join(" · ") : "Sin materiales permitidos"}</p>
      <div className="mt-4 flex flex-wrap gap-2">{canManage ? <Button variant="secondary" onClick={() => edit(point)}>Editar</Button> : null}{canManage ? <Button variant="secondary" onClick={() => void toggle(point)}>{point.is_active ? "Desactivar" : "Activar"}</Button> : null}</div>
    </article>; })}</div> : !editing ? <p className="rounded-xl border border-dashed bg-white p-6 text-center text-sm text-slate-500">Todavía no hay acopios creados para este evento.</p> : null}
    <section className="space-y-3 rounded-xl border bg-white p-4">
      <div><h4 className="font-bold">Registros de acopio</h4><p className="text-sm text-slate-500">El RUT se muestra parcialmente oculto.</p></div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5"><label className="relative"><Search className="absolute left-3 top-3 h-4 w-4 text-slate-400"/><input aria-label="Buscar persona" className="w-full rounded-lg border py-2 pl-9 pr-3" placeholder="Buscar persona" value={search} onChange={e => setSearch(e.target.value)}/></label><select aria-label="Filtrar por acopio" className="rounded-lg border bg-white p-2" value={pointFilter} onChange={e => setPointFilter(e.target.value)}><option value="">Todos los acopios</option>{points.map(point => <option value={point.id} key={point.id}>{point.code} · {point.name}</option>)}</select><select aria-label="Filtrar por material" className="rounded-lg border bg-white p-2" value={typeFilter} onChange={e => setTypeFilter(e.target.value)}><option value="">Todos los materiales</option>{types.map(type => <option value={type.id} key={type.id}>{type.name}</option>)}</select><input aria-label="Desde fecha" type="date" className="rounded-lg border bg-white p-2" value={dateFrom} onChange={e => setDateFrom(e.target.value)}/><input aria-label="Hasta fecha" type="date" className="rounded-lg border bg-white p-2" value={dateTo} onChange={e => setDateTo(e.target.value)}/></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="border-b text-xs uppercase text-slate-500"><tr><th className="py-2">Fecha</th><th>Acopio</th><th>Material</th><th>Peso</th><th>Persona</th><th>RUT</th><th>Sync</th></tr></thead><tbody className="divide-y">{records.map(record => <tr key={record.id}><td className="py-3">{dateLabel(record.recorded_at)}</td><td>{record.collection_point_code} · {record.collection_point_name}</td><td>{record.waste_type_name}</td><td>{Number(record.weight_kg).toLocaleString("es-CL")} kg</td><td>{record.submitter_name}</td><td>{record.submitter_rut_masked}</td><td><span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-semibold text-emerald-800">Sincronizado</span></td></tr>)}{!records.length ? <tr><td className="py-5 text-center text-slate-500" colSpan={7}>No hay registros para estos filtros.</td></tr> : null}</tbody></table></div>
    </section>
    {formQrOpen && publicForm ? <div role="dialog" aria-modal="true" aria-label="QR general del formulario Greenway" className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4" onClick={() => setFormQrOpen(false)}><div className="w-full max-w-sm rounded-2xl bg-white p-5 text-center" onClick={e => e.stopPropagation()}><h3 className="text-lg font-bold">Formulario Greenway · QR general</h3>{publicForm.qr_data_url ? <img className="mx-auto my-4 h-64 w-64" src={publicForm.qr_data_url} alt="Código QR general del evento"/> : null}<p className="break-all text-xs text-slate-500">{publicForm.public_url}</p><div className="mt-4 flex justify-center gap-2">{publicForm.qr_data_url ? <a className="inline-flex min-h-10 items-center rounded-xl bg-emerald-700 px-4 text-sm font-semibold text-white" href={publicForm.qr_data_url} download="greenway-formulario-qr.png">Descargar QR</a> : null}<Button variant="secondary" onClick={() => setFormQrOpen(false)}>Cerrar</Button></div></div></div> : null}
  </section>;
}
