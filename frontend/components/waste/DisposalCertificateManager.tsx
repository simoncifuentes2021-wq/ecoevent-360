"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Download, FileCheck2, LoaderCircle, X } from "lucide-react";
import { API_URL } from "@/lib/constants";
import { getStoredToken } from "@/lib/auth";
import { ApiError, api } from "@/lib/api/index";
import { Button } from "@/components/ui/button";
import type { DisposalCertificateContext, DisposalCertificateCreate, DisposalCertificateListItem } from "@/types/disposal-certificate";

type MaterialDraft = { id: string; name: string; received: number; selected: boolean; final: string };
const kg = (value: number | string) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: 3 }).format(Number(value));

async function downloadPdf(id: string, filename: string) {
  const token = getStoredToken();
  const response = await fetch(API_URL + "/disposal-certificates/" + id + "/pdf", { headers: token ? { Authorization: "Bearer " + token } : {} });
  if (!response.ok) {
    let message = "No se pudo descargar el certificado.";
    try { const body = await response.json() as { detail?: string }; message = body.detail || message; } catch {}
    throw new ApiError(response.status, message);
  }
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

export function DisposalCertificateManager({ eventId }: { eventId: string }) {
  const [open, setOpen] = useState(false);
  const [context, setContext] = useState<DisposalCertificateContext | null>(null);
  const [materials, setMaterials] = useState<MaterialDraft[]>([]);
  const [recipientName, setRecipientName] = useState("");
  const [recipientRut, setRecipientRut] = useState("");
  const [eventName, setEventName] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const value = await api.get<DisposalCertificateContext>("/events/" + eventId + "/disposal-certificates/context");
      setContext(value);
      setRecipientName(value.recipient_name);
      setRecipientRut(value.recipient_rut || "");
      setEventName(value.event_name);
      setMaterials(value.materials.map(item => ({
        id: item.waste_type_id,
        name: item.name,
        received: Number(item.received_kg),
        selected: Number(item.received_kg) > 0,
        final: String(item.received_kg),
      })));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudieron cargar los datos del certificado.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  const selected = useMemo(() => materials.filter(item => item.selected), [materials]);
  const total = selected.reduce((sum, item) => sum + (Number(item.final) || 0), 0);
  const invalid = selected.some(item => Number(item.final) <= 0 || Number(item.final) > item.received);

  function requestBody(): DisposalCertificateCreate {
    return {
      recipient_name: recipientName.trim(),
      recipient_rut: recipientRut.trim(),
      event_name: eventName.trim(),
      materials: selected.map(item => ({ waste_type_id: item.id, final_weight_kg: Number(item.final) })),
    };
  }

  async function preview() {
    const previewWindow = window.open("about:blank", "_blank");
    setPreviewing(true);
    setError("");
    try {
      const token = getStoredToken();
      const response = await fetch(API_URL + "/events/" + eventId + "/disposal-certificates/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: "Bearer " + token } : {}) },
        body: JSON.stringify(requestBody()),
      });
      if (!response.ok) {
        let message = "No se pudo preparar la vista previa.";
        try { const body = await response.json() as { detail?: string }; message = body.detail || message; } catch {}
        throw new ApiError(response.status, message);
      }
      const url = URL.createObjectURL(await response.blob());
      if (previewWindow) previewWindow.location.href = url;
      else {
        const link = document.createElement("a"); link.href = url; link.target = "_blank"; link.rel = "noreferrer"; link.click();
      }
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch (reason) {
      previewWindow?.close();
      setError(reason instanceof Error ? reason.message : "No se pudo preparar la vista previa.");
    } finally {
      setPreviewing(false);
    }
  }

  async function issue() {
    if (!selected.length || invalid || !recipientName.trim() || !eventName.trim()) return;
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const created = await api.post<DisposalCertificateListItem & { file_size: number }>("/events/" + eventId + "/disposal-certificates", requestBody());
      setNotice("Certificado " + created.certificate_number + " emitido y guardado.");
      await load();
      setDownloading(created.id);
      await downloadPdf(created.id, created.certificate_number + ".pdf");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudo emitir el certificado.");
    } finally {
      setDownloading(null);
      setSaving(false);
    }
  }

  async function download(item: DisposalCertificateListItem) {
    setDownloading(item.id);
    setError("");
    try { await downloadPdf(item.id, item.certificate_number + ".pdf"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo descargar el certificado."); }
    finally { setDownloading(null); }
  }

  return <>
    <section className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-white to-emerald-50/70 p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-start gap-3">
          <span className="rounded-xl bg-emerald-100 p-2.5 text-emerald-800"><FileCheck2 className="h-5 w-5" /></span>
          <div><h4 className="font-bold text-slate-900">Certificados de disposición final</h4><p className="mt-1 text-sm text-slate-600">Los datos de Greenway y del director se reutilizan desde Documentos. El cliente y su RUT se toman de esta faena.</p></div>
        </div>
        <Button disabled={loading || !context} onClick={() => { setError(""); setNotice(""); setOpen(true); }}><FileCheck2 className="h-4 w-4" />Preparar certificado</Button>
      </div>
      {notice ? <p role="status" className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p> : null}
      {error && !open ? <p role="alert" className="mt-3 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      {context?.certificates.length ? <div className="mt-4 divide-y rounded-xl border bg-white">{context.certificates.map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 p-3"><div><p className="text-sm font-semibold text-slate-900">{item.certificate_number} · {item.recipient_name}</p><p className="text-xs text-slate-600">{new Date(item.certificate_date + "T12:00:00").toLocaleDateString("es-CL")} · {kg(item.total_kg)} kg</p></div><Button size="sm" variant="secondary" disabled={downloading === item.id} onClick={() => void download(item)}><Download className="h-4 w-4" />{downloading === item.id ? "Preparando…" : "Descargar PDF"}</Button></div>)}</div> : null}
    </section>
    {open ? <div className="fixed inset-0 z-[70] flex items-start justify-center overflow-y-auto bg-slate-950/50 p-3 sm:p-6" role="dialog" aria-modal="true" aria-label="Preparar certificado de disposición final"><section className="my-auto w-full max-w-4xl rounded-2xl bg-white shadow-2xl">
      <header className="flex items-start justify-between gap-4 border-b p-5 sm:p-6"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Certificado · Nuevo documento</p><h3 className="mt-1 text-xl font-bold text-slate-950">{eventName || "Preparar certificado"}</h3><p className="mt-1 text-sm text-slate-600">Empresa certificada: <strong>{recipientName || "Cargando…"}</strong>{recipientRut ? " · RUT " + recipientRut : ""}</p><p className="mt-1 text-xs text-slate-500">Puedes ajustar estos datos solo para este certificado, sin cambiar la ficha de la faena ni del cliente.</p></div><button type="button" aria-label="Cerrar" onClick={() => setOpen(false)} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100"><X className="h-5 w-5" /></button></header>
      <div className="space-y-5 p-5 sm:p-6">
        {loading ? <p className="flex items-center gap-2 text-sm text-slate-600"><LoaderCircle className="h-4 w-4 animate-spin" />Cargando materiales del evento…</p> : null}
        {error ? <p role="alert" className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
        {!loading && !materials.length ? <p className="rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Este evento todavía no tiene materiales registrados en los acopios.</p> : null}
        <details className="rounded-xl border border-slate-200 bg-white p-4">
          <summary className="cursor-pointer font-semibold text-slate-900">Editar datos que aparecerán en el certificado</summary>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <label className="grid gap-1.5 text-sm font-medium text-slate-700">Empresa a quien se certifica
              <input required maxLength={240} className="h-10 rounded-lg border border-slate-300 px-3" value={recipientName} onChange={(event) => setRecipientName(event.target.value)} />
            </label>
            <label className="grid gap-1.5 text-sm font-medium text-slate-700">RUT de la empresa
              <input maxLength={30} className="h-10 rounded-lg border border-slate-300 px-3" value={recipientRut} onChange={(event) => setRecipientRut(event.target.value)} placeholder="Opcional" />
            </label>
            <label className="grid gap-1.5 text-sm font-medium text-slate-700 sm:col-span-2">Nombre del evento que aparecerá
              <input required maxLength={240} className="h-10 rounded-lg border border-slate-300 px-3" value={eventName} onChange={(event) => setEventName(event.target.value)} />
            </label>
            <p className="text-xs text-slate-500 sm:col-span-2">Los cambios se aplican solo a este certificado y quedan guardados en su copia final.</p>
          </div>
        </details>
        {materials.length ? <div>
          <div className="mb-2 flex flex-wrap items-end justify-between gap-2"><div><h4 className="font-bold">Materiales y cantidades</h4><p className="text-xs text-slate-600">Selecciona lo que se entregó. El certificado incluirá solo estas cantidades finales.</p></div><p className="text-sm font-semibold text-emerald-800">Total: {kg(total)} kg</p></div>
          <div className="overflow-hidden rounded-xl border">
            <div className="grid grid-cols-[auto_1fr_7rem_8rem] gap-2 bg-slate-50 px-3 py-2 text-xs font-semibold text-slate-600"><span /><span>Material</span><span className="text-right">Recibido</span><span className="text-right">Entregado (kg)</span></div>
            {materials.map(item => <div key={item.id} className="grid grid-cols-[auto_1fr_7rem_8rem] items-center gap-2 border-t px-3 py-2"><input aria-label={"Incluir " + item.name} type="checkbox" checked={item.selected} onChange={event => setMaterials(rows => rows.map(row => row.id === item.id ? { ...row, selected: event.target.checked } : row))} /><span className="text-sm font-medium">{item.name}</span><span className="text-right text-sm text-slate-500">{kg(item.received)} kg</span><input aria-label={"Cantidad entregada de " + item.name + " en kg"} disabled={!item.selected} type="number" min="0.001" max={item.received} step="0.001" className="w-full rounded-lg border p-2 text-right text-sm disabled:bg-slate-100" value={item.final} onChange={event => setMaterials(rows => rows.map(row => row.id === item.id ? { ...row, final: event.target.value } : row))} /></div>)}
          </div>
        </div> : null}
        <p className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">La fecha, el texto de disposición y la firma del director se completan con la configuración guardada en Documentos.</p>
        <div className="flex flex-wrap justify-end gap-2"><Button variant="secondary" onClick={() => setOpen(false)}>Cerrar</Button><Button variant="secondary" disabled={previewing || loading || !selected.length || invalid || !recipientName.trim() || !eventName.trim()} onClick={() => void preview()}>{previewing ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}{previewing ? "Preparando vista previa…" : "Vista previa PDF"}</Button><Button disabled={saving || previewing || loading || !selected.length || invalid || !recipientName.trim() || !eventName.trim()} onClick={() => void issue()}>{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <FileCheck2 className="h-4 w-4" />}{saving ? "Emitiendo…" : "Emitir certificado"}</Button></div>
      </div>
    </section></div> : null}
  </>;
}
