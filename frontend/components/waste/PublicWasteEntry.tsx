"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CheckCircle2, CloudOff, Leaf, LoaderCircle, LogOut, Plus, RefreshCw, Wifi, WifiOff } from "lucide-react";
import { getPublicCollectionPoint, submitPublicWasteBatch } from "@/lib/api/waste";
import { ApiError } from "@/lib/api";
import { cachePublicForm, clearWorkerProfile, createUuid, deletePendingRecord, listTokenRecords, migrateLegacyCollectionQueue, readCachedPublicForm, readWorkerProfile, savePendingRecord, saveWorkerProfile, type QueuedWasteRecord } from "@/lib/waste-offline";
import type { PublicCollectionPoint } from "@/types/waste";

const DEVICE_KEY = "ecoevent.waste.device-id";
const rejectionMessage = (reason: string) => ({
  WASTE_TYPE_NOT_ALLOWED: "El material ya no está permitido en este acopio. Solicita autorización al supervisor.",
  COLLECTION_POINT_INACTIVE: "El acopio fue desactivado y el registro no se sincronizó.",
  FORM_CLOSED_AFTER_RECORD: "El formulario se cerró antes de la hora de este registro.",
  INVALID_RUT: "El RUT no es válido. Corrígelo para sincronizar este registro.",
  RUT_INVALID: "El RUT no es válido. Corrígelo para sincronizar este registro.",
}[reason] || reason.replaceAll("_", " "));
const normalizeRut = (value: string): string | null => {
  const normalized = value.replace(/[.\-\s]/g, "").toUpperCase();
  if (normalized.length < 2 || !/^\d+$/.test(normalized.slice(0, -1))) return null;
  const total = Array.from(normalized.slice(0, -1)).reverse().reduce((sum, digit, index) => sum + Number(digit) * (index % 6 + 2), 0);
  const remainder = 11 - total % 11;
  const verifier = remainder === 11 ? "0" : remainder === 10 ? "K" : String(remainder);
  return normalized[normalized.length - 1] === verifier ? `${normalized.slice(0, -1)}-${verifier}` : null;
};
const statusLabel = (status: QueuedWasteRecord["status"]) => ({ PENDING: "Pendiente", SYNCED: "Sincronizado", REJECTED: "Rechazado" })[status];
const uuid = () => typeof window !== "undefined" ? (window.localStorage.getItem(DEVICE_KEY) || (() => { const id = createUuid(); window.localStorage.setItem(DEVICE_KEY, id); return id; })()) : "";

export function PublicWasteEntry({ token }: { token: string }) {
  const [form, setForm] = useState<PublicCollectionPoint | null>(null);
  const [records, setRecords] = useState<QueuedWasteRecord[]>([]);
  const [name, setName] = useState("");
  const [rut, setRut] = useState("");
  const [typeId, setTypeId] = useState("");
  const [pointId, setPointId] = useState("");
  const [weight, setWeight] = useState("");
  const [online, setOnline] = useState(typeof navigator === "undefined" || navigator.onLine);
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [confirmFinish, setConfirmFinish] = useState(false);
  const [finishing, setFinishing] = useState(false);
  const weightInput = useRef<HTMLInputElement>(null);

  const refreshRecords = useCallback(async () => { try { setRecords(await listTokenRecords(token)); } catch { /* Storage can be unavailable in private browsing. */ } }, [token]);
  const syncPending = useCallback(async () => {
    if (!navigator.onLine) return;
    const pending = (await listTokenRecords(token)).filter(item => item.status === "PENDING");
    if (!pending.length) return;
    try {
      const response = await submitPublicWasteBatch(token, pending.map(({ token: _token, status: _status, synced_at: _synced, error: _error, clear_after_sync: _clear, ...payload }) => payload));
      const accepted = new Map((Array.isArray(response.synced) ? response.synced : []).map(item => [item.client_generated_id, item.synced_at]));
      const rejected = new Map((Array.isArray(response.rejected) ? response.rejected : []).map(item => [item.client_generated_id, item.reason]));
      await Promise.all(pending.map(item => accepted.has(item.client_generated_id)
        ? item.clear_after_sync ? deletePendingRecord(item.client_generated_id) : savePendingRecord({ ...item, status: "SYNCED", synced_at: accepted.get(item.client_generated_id) })
        : rejected.has(item.client_generated_id) ? savePendingRecord({ ...item, status: "REJECTED", error: rejected.get(item.client_generated_id) }) : Promise.resolve()));
      if (accepted.size) setMessage(`${accepted.size} registro${accepted.size === 1 ? "" : "s"} sincronizado${accepted.size === 1 ? "" : "s"}.`);
      if (rejected.size) setError(rejectionMessage(Array.from(rejected.values())[0]));
      await refreshRecords();
    } catch (err) {
      if (err instanceof ApiError) {
        const rutError = JSON.stringify(err.rawDetail || err.message).toLowerCase().includes("rut");
        setError(rutError ? "El RUT de los registros pendientes no es válido. Corrígelo en el campo RUT; se actualizarán al salir del campo." : err.message);
      }
      // Network errors leave the durable queue untouched for the next retry.
    }
  }, [refreshRecords, token]);

  useEffect(() => {
    let live = true;
    const updateConnection = () => { setOnline(navigator.onLine); if (navigator.onLine) void syncPending(); };
    window.addEventListener("online", updateConnection); window.addEventListener("offline", updateConnection);
    void (async () => {
      try {
        await refreshRecords();
        try {
          const rawMetadata = await getPublicCollectionPoint(token);
          if (!Array.isArray(rawMetadata.collection_points)) throw new Error("El formulario guardado tiene un formato antiguo. Conéctate para actualizarlo.");
          const metadata = { ...rawMetadata, collection_points: rawMetadata.collection_points.map(point => ({
            ...point,
            allowed_waste_types: Array.isArray(point.allowed_waste_types) ? point.allowed_waste_types : [],
          })) };
          if (!live) return;
          const profile = await readWorkerProfile(metadata.event_id); if (profile) { setName(profile.name); setRut(profile.rut); }
          setForm(metadata); setPointId(metadata.collection_points[0]?.id || ""); setTypeId(metadata.collection_points[0]?.allowed_waste_types[0]?.id || ""); await migrateLegacyCollectionQueue(token, metadata); await cachePublicForm(token, metadata); await refreshRecords();
          if ("serviceWorker" in navigator) {
            const registration = await navigator.serviceWorker.register("/acopios/sw.js", { scope: "/acopios/" });
            await navigator.serviceWorker.ready;
            const worker = registration.active || navigator.serviceWorker.controller;
            if (worker) await new Promise<void>((resolve, reject) => {
              const channel = new MessageChannel();
              const timeout = window.setTimeout(() => reject(new Error("No se pudo preparar el modo sin conexión.")), 12000);
              channel.port1.onmessage = event => { if (event.data?.type === "FORM_CACHED") { window.clearTimeout(timeout); resolve(); } };
              worker.postMessage({ type: "CACHE_FORM_URL", url: window.location.href }, [channel.port2]);
            });
            setReady(true);
          }
          if (navigator.onLine) void syncPending();
        } catch (err) {
          if (err instanceof ApiError) { if (live) setError(err.message); return; }
          const cached = await readCachedPublicForm(token);
          if (live && cached && Array.isArray(cached.collection_points)) { const safeCached = { ...cached, collection_points: cached.collection_points.map(point => ({ ...point, allowed_waste_types: Array.isArray(point.allowed_waste_types) ? point.allowed_waste_types : [] })) }; const profile = await readWorkerProfile(cached.event_id); if (profile) { setName(profile.name); setRut(profile.rut); } setForm(safeCached); setPointId(safeCached.collection_points[0]?.id || ""); setTypeId(safeCached.collection_points[0]?.allowed_waste_types[0]?.id || ""); setReady(true); }
          else if (live) setError(err instanceof Error ? err.message : "No se pudo abrir este formulario.");
        }
      } finally { if (live) setLoading(false); }
    })();
    return () => { live = false; window.removeEventListener("online", updateConnection); window.removeEventListener("offline", updateConnection); };
  }, [refreshRecords, syncPending, token]);

  const pendingCount = useMemo(() => records.filter(item => item.status === "PENDING").length, [records]);
  const rejectedCount = useMemo(() => records.filter(item => item.status === "REJECTED").length, [records]);
  const todaySummary = useMemo(() => {
    const today = new Date().toLocaleDateString("sv-SE");
    const byMaterial = new Map<string, { name: string; weight: number }>();
    let total = 0;
    for (const record of records) {
      if (record.status === "REJECTED" || new Date(record.recorded_at).toLocaleDateString("sv-SE") !== today) continue;
      const point = form?.collection_points.find(item => item.id === record.collection_point_id);
      const material = point?.allowed_waste_types?.find(item => item.id === record.waste_type_id);
      const name = material?.name || "Material";
      const weight = Number(record.weight_kg) || 0;
      total += weight;
      const previous = byMaterial.get(name) || { name, weight: 0 };
      previous.weight += weight;
      byMaterial.set(name, previous);
    }
    return { total, materials: Array.from(byMaterial.values()).sort((a, b) => b.weight - a.weight) };
  }, [form, records]);
  const collectionPoints = Array.isArray(form?.collection_points) ? form.collection_points : [];
  const selectedPoint = collectionPoints.find(point => point.id === pointId);
  const allowedTypes = selectedPoint?.allowed_waste_types || [];
  function changePoint(nextId: string) { setPointId(nextId); setTypeId(collectionPoints.find(point => point.id === nextId)?.allowed_waste_types[0]?.id || ""); }
  async function saveWorker() {
    if (!form || !name.trim()) return;
    const correctedRut = normalizeRut(rut);
    if (!correctedRut) return;
    setRut(correctedRut);
    await saveWorkerProfile(form.event_id, { name: name.trim(), rut: correctedRut });
    setError("");
    const pending = (await listTokenRecords(token)).filter(item => item.status === "PENDING");
    const updates = pending.filter(item => item.submitter_rut !== correctedRut || item.submitter_name !== name.trim());
    if (!updates.length) return;
    await Promise.all(updates.map(item => savePendingRecord({ ...item, submitter_name: name.trim(), submitter_rut: correctedRut, error: undefined })));
    await refreshRecords();
    setError("");
    setMessage(`${updates.length} registro${updates.length === 1 ? " pendiente" : "s pendientes"} actualizado${updates.length === 1 ? "" : "s"} con el RUT corregido.`);
    if (navigator.onLine) await syncPending();
  }
  async function finishShift() {
    if (!form) return;
    setFinishing(true);
    setError("");
    try {
      await clearWorkerProfile(form.event_id);
      const pending = records.filter(item => item.status === "PENDING");
      await Promise.all(records.filter(item => item.status === "SYNCED").map(item => deletePendingRecord(item.client_generated_id)));
      await Promise.all(pending.map(item => savePendingRecord({ ...item, clear_after_sync: true })));
      const remaining = records.filter(item => item.status !== "SYNCED").map(item => item.status === "PENDING" ? { ...item, clear_after_sync: true } : item);
      setRecords(remaining);
      setName("");
      setRut("");
      setConfirmFinish(false);
      const rejectedCount = remaining.filter(item => item.status === "REJECTED").length;
      setMessage(`Jornada finalizada. Se borró el perfil y el historial sincronizado.${pending.length ? ` Se conservaron ${pending.length} registros pendientes hasta que se sincronicen.` : ""}${rejectedCount ? ` Se conservaron ${rejectedCount} registros rechazados para revisarlos.` : ""}`);
      if (navigator.onLine && pending.length) await syncPending();
    } catch {
      setError("No se pudieron limpiar los datos de esta jornada. Inténtalo nuevamente.");
    } finally {
      setFinishing(false);
    }
  }
  async function registerWaste() {
    setError(""); setMessage("");
    if (!form) { setError("El formulario todavía no está disponible."); return; }
    const normalizedWeight = Number(weight.trim().replace(",", "."));
    const normalizedRut = normalizeRut(rut);
    if (!name.trim()) { setError("Escribe el nombre del trabajador."); return; }
    if (!rut.trim()) { setError("Escribe el RUT del trabajador."); return; }
    if (!normalizedRut) { setError("El RUT no es válido. Revisa el número y el dígito verificador."); return; }
    if (!pointId) { setError("Selecciona el acopio donde estás registrando."); return; }
    if (!allowedTypes.some(item => item.id === typeId)) { setError("Selecciona un material permitido para este acopio."); return; }
    if (!Number.isFinite(normalizedWeight) || normalizedWeight <= 0) { setError("Ingresa un peso mayor que cero."); weightInput.current?.focus(); return; }
    setRut(normalizedRut);
    await saveWorkerProfile(form.event_id, { name: name.trim(), rut: normalizedRut });
    const item = { client_generated_id: createUuid(), device_id: uuid(), collection_point_id: pointId, waste_type_id: typeId, weight_kg: normalizedWeight, submitter_name: name.trim(), submitter_rut: normalizedRut, recorded_at: new Date().toISOString() };
    const queued: QueuedWasteRecord = { ...item, token, status: "PENDING" };
    setSaving(true);
    try {
      await savePendingRecord(queued); await refreshRecords(); setWeight("");
      const materialName = allowedTypes.find(item => item.id === typeId)?.name || "Material";
      setMessage(`Guardado: ${materialName} · ${normalizedWeight} kg.`);
      if (navigator.onLine) await syncPending();
      else setMessage(`Guardado en este dispositivo: ${materialName} · ${normalizedWeight} kg. Se enviará al recuperar conexión.`);
    } catch { setError("No se pudo guardar en este dispositivo. Revisa el espacio disponible."); }
    finally { setSaving(false); window.setTimeout(() => weightInput.current?.focus(), 0); }
  }

  if (loading && !form) return <main className="grid min-h-dvh place-items-center bg-emerald-950 p-6 text-white"><LoaderCircle className="h-8 w-8 animate-spin"/><span className="sr-only">Cargando acopio</span></main>;
  if (!form) return <main className="grid min-h-dvh place-items-center bg-slate-50 p-5"><div className="max-w-sm rounded-2xl bg-white p-6 text-center shadow"><h1 className="text-xl font-bold">Formulario no disponible</h1><p className="mt-2 text-slate-600">{error || "El registro de residuos de este evento está cerrado."}</p></div></main>;

  return <main className="min-h-dvh bg-[#f4f7f4] pb-10 text-slate-950">
    <header className="bg-emerald-950 px-5 pb-6 pt-7 text-white"><div className="mx-auto max-w-lg"><div className="flex items-center gap-2 text-emerald-200"><Leaf className="h-5 w-5"/><span className="text-xs font-bold uppercase tracking-[0.18em]">Greenway · EcoEvent 360</span></div><div className="mt-5 flex items-start justify-between gap-3"><div><p className="text-sm text-emerald-100">{form.event_name}</p><h1 className="mt-1 text-2xl font-extrabold">Registro de acopios</h1></div><div className={`rounded-full px-3 py-2 text-xs font-bold ${online ? "bg-emerald-800 text-emerald-100" : "bg-amber-300 text-amber-950"}`}>{online ? <><Wifi className="mr-1 inline h-3.5 w-3.5"/>En línea</> : <><WifiOff className="mr-1 inline h-3.5 w-3.5"/>Sin conexión</>}</div></div></div></header>
    <div className="mx-auto max-w-lg space-y-4 px-4 pt-4">
      <div role="status" className={`rounded-xl border px-4 py-3 text-sm font-semibold ${ready ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-amber-200 bg-amber-50 text-amber-900"}`}>{ready ? <><CheckCircle2 className="mr-2 inline h-4 w-4"/>Formulario listo para trabajar sin conexión</> : "Preparando el formulario para uso sin conexión…"}</div>
      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="text-base font-bold">Trabajador</h2><label className="block text-sm font-semibold">Nombre<input autoComplete="name" className="mt-1.5 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-base" value={name} onChange={e => setName(e.target.value)} onBlur={() => void saveWorker()}/></label><label className="block text-sm font-semibold">RUT<input autoComplete="off" inputMode="text" placeholder="12345678-9" className="mt-1.5 min-h-12 w-full rounded-xl border border-slate-300 px-3 text-base" value={rut} onChange={e => setRut(e.target.value)} onBlur={() => void saveWorker()}/></label></section>
      {confirmFinish ? <section role="alertdialog" aria-label="Confirmar finalizaci&#xF3;n de jornada" className="space-y-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950"><h2 className="font-bold">&#xBF;Finalizar esta jornada?</h2><p className="text-sm">Se borrar&#xE1;n el nombre, el RUT y el historial ya sincronizado de este dispositivo. Los registros pendientes o rechazados se conservar&#xE1;n para no perderlos.</p>{pendingCount || rejectedCount ? <p className="text-sm font-semibold">Quedan {pendingCount} pendientes y {rejectedCount} rechazados guardados localmente.</p> : null}<div className="flex gap-2"><button type="button" disabled={finishing} onClick={() => void finishShift()} className="min-h-11 flex-1 rounded-xl bg-emerald-700 px-3 text-sm font-bold text-white disabled:opacity-50">{finishing ? "Limpiando..." : "Finalizar y limpiar"}</button><button type="button" disabled={finishing} onClick={() => setConfirmFinish(false)} className="min-h-11 rounded-xl border border-amber-300 px-3 text-sm font-semibold">Cancelar</button></div></section> : <button type="button" onClick={() => setConfirmFinish(true)} className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700"><LogOut className="h-4 w-4"/>Finalizar jornada</button>}
      <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="text-base font-bold">Registrar material</h2><fieldset><legend className="mb-2 text-sm font-semibold">¿En qué acopio estás registrando?</legend><div className="grid grid-cols-2 gap-2">{collectionPoints.map(point => <button type="button" key={point.id} onClick={() => changePoint(point.id)} className={`min-h-16 rounded-xl border p-3 text-left ${point.id === pointId ? "border-emerald-700 bg-emerald-50 ring-1 ring-emerald-700" : "border-slate-300"}`}><span className="block text-sm font-semibold">{point.name}</span><span className="mt-1 block text-xs text-slate-500">{point.code}</span></button>)}</div></fieldset><label className="block text-sm font-semibold">Material<select className="mt-1.5 min-h-12 w-full rounded-xl border border-slate-300 bg-white px-3 text-base" value={typeId} onChange={e => { setTypeId(e.target.value); requestAnimationFrame(() => weightInput.current?.focus()); }} disabled={!allowedTypes.length}>{allowedTypes.map(type => <option key={type.id} value={type.id}>{type.name}</option>)}</select></label>{!allowedTypes.length ? <p className="text-sm text-amber-800">Este acopio aún no tiene materiales permitidos.</p> : null}<label className="block text-sm font-semibold">Peso en kilogramos<div className="mt-1.5 flex items-center rounded-xl border border-slate-300 focus-within:border-emerald-700 focus-within:ring-2 focus-within:ring-emerald-100"><input ref={weightInput} aria-label="Peso en kilogramos" inputMode="decimal" type="text" pattern="[0-9]+([.,][0-9]+)?" placeholder="0,0" className="min-h-20 min-w-0 flex-1 rounded-xl px-4 text-4xl font-extrabold outline-none" value={weight} onChange={e => setWeight(e.target.value)} onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); void registerWaste(); } }}/><span className="px-4 text-lg font-bold text-slate-500">kg</span></div></label><button type="button" disabled={saving || !ready || !allowedTypes.length} onClick={() => void registerWaste()} className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 text-lg font-bold text-white shadow-sm hover:bg-emerald-800 disabled:opacity-50">{saving ? <LoaderCircle className="h-5 w-5 animate-spin"/> : <Plus className="h-5 w-5"/>}Guardar registro</button></section>
      {error ? <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800">{error}</p> : null}{message ? <p role="status" className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-900">{message}</p> : null}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><h2 className="font-bold">Resumen de hoy</h2><p className="mt-1 text-2xl font-extrabold text-emerald-800">{todaySummary.total.toLocaleString("es-CL", { maximumFractionDigits: 1 })} kg</p>{todaySummary.materials.length ? <ul className="mt-2 space-y-1 text-sm">{todaySummary.materials.map(item => <li key={item.name} className="flex justify-between gap-3"><span>{item.name}</span><b>{item.weight.toLocaleString("es-CL", { maximumFractionDigits: 1 })} kg</b></li>)}</ul> : <p className="text-sm text-slate-500">Aún no hay registros hoy.</p>}</section>
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><div className="flex items-center justify-between"><h2 className="font-bold">Registros de este dispositivo</h2><button type="button" onClick={() => void syncPending()} aria-label="Sincronizar registros" className="rounded-lg p-2 text-emerald-800"><RefreshCw className="h-5 w-5"/></button></div><p className="mt-1 text-sm text-slate-500">{pendingCount ? `${pendingCount} pendiente${pendingCount === 1 ? "" : "s"} por sincronizar` : "Todo sincronizado"}</p>{!online ? <p className="mt-3 rounded-lg bg-amber-50 p-2 text-xs text-amber-900"><CloudOff className="mr-1 inline h-4 w-4"/>El historial se guarda localmente y sobrevive al cierre del navegador.</p> : null}<ul className="mt-3 divide-y divide-slate-100">{records.slice(0, 8).map(record => { const point = collectionPoints.find(item => item.id === record.collection_point_id); const material = point?.allowed_waste_types?.find(item => item.id === record.waste_type_id); const badge = record.status === "PENDING" ? "bg-amber-100 text-amber-900" : record.status === "REJECTED" ? "bg-red-100 text-red-900" : "bg-emerald-100 text-emerald-900"; return <li key={record.client_generated_id} className="flex items-center justify-between gap-3 py-2 text-sm"><span><b>{material?.name || "Material"}</b><span className="ml-2 text-slate-500">{record.weight_kg} kg</span><span className="block text-xs text-slate-400">{point?.code} · {new Date(record.recorded_at).toLocaleTimeString("es-CL", { hour: "2-digit", minute: "2-digit" })}</span>{record.error ? <span className="block text-xs text-red-700">{rejectionMessage(record.error)}</span> : null}</span><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${badge}`}>{statusLabel(record.status)}</span></li>; })}</ul></section>
      <p className="pb-5 text-center text-xs text-slate-500">Los datos de trabajador se conservan en este dispositivo para la jornada.</p>
    </div>
  </main>;
}
