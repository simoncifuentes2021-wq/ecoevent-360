"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Download, Printer } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { documentApi } from "@/lib/api/documents";

type PersonRow = { personId: string; name: string; rut: string };

export function PaperPrintBatchModal({
  eventId,
  eventName,
  people,
  onChanged,
  onClose,
}: {
  eventId: string;
  eventName: string;
  people: PersonRow[];
  onChanged: () => void;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<Set<string>>(() => new Set(people.map((person) => person.personId)));
  const [kinds, setKinds] = useState<Array<"CONTRACT" | "EPP">>(["CONTRACT", "EPP"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [pdfUrl, setPdfUrl] = useState("");
  const [stats, setStats] = useState<{ documents: number; pages: number } | null>(null);
  const [batches, setBatches] = useState<Awaited<ReturnType<typeof documentApi.paperBatches>>>([]);
  const frame = useRef<HTMLIFrameElement>(null);
  const selectedPeople = useMemo(() => people.filter((person) => selected.has(person.personId)), [people, selected]);

  useEffect(() => () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl); }, [pdfUrl]);
  useEffect(() => { void documentApi.paperBatches(eventId).then(setBatches).catch(() => setBatches([])); }, [eventId]);

  function toggleKind(kind: "CONTRACT" | "EPP") {
    setKinds((current) => current.includes(kind) ? current.filter((item) => item !== kind) : [...current, kind]);
    setPdfUrl(""); setStats(null); setError("");
  }

  async function prepare() {
    if (!selectedPeople.length || !kinds.length) return;
    setBusy(true); setError("");
    try {
      const result = await documentApi.paperPrintBatch(eventId, selectedPeople.map((person) => person.personId), kinds);
      setPdfUrl(URL.createObjectURL(result.blob));
      setStats({ documents: result.documents, pages: result.pages });
      setBatches(await documentApi.paperBatches(eventId));
      onChanged();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo preparar el lote para impresión.");
    } finally { setBusy(false); }
  }

  async function reopenBatch(id: string) {
    setBusy(true); setError("");
    try { const blob = await documentApi.paperBatchPdf(id); setPdfUrl(URL.createObjectURL(blob)); const batch = batches.find((item) => item.id === id); if (batch) setStats({ documents: batch.document_count, pages: batch.page_count }); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo recuperar el lote."); }
    finally { setBusy(false); }
  }

  function downloadPdf() {
    if (!pdfUrl) return;
    const anchor = document.createElement("a"); anchor.href = pdfUrl;
    anchor.download = `documentos-firma-papel-${eventId}.pdf`; anchor.click();
  }

  return <ModalShell size="lg" title="Imprimir lote en papel" description={`${eventName} · flujo independiente de la firma electrónica. No envía correos ni enlaces.`} onClose={onClose}>
    <div className="space-y-4">
      {!pdfUrl ? <>
        {batches.length > 0 && <section className="rounded-xl border p-3"><h3 className="mb-2 text-sm font-semibold">Lotes anteriores · puedes reimprimirlos</h3><div className="max-h-32 space-y-1 overflow-auto">{batches.map((batch) => <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2 text-xs" key={batch.id}><span>{new Date(batch.created_at).toLocaleString("es-CL")} · {batch.people_count} personas · {batch.document_count} documentos · {batch.page_count} págs.</span><Button size="sm" variant="secondary" disabled={busy} onClick={() => void reopenBatch(batch.id)}><Download className="h-4 w-4"/>Abrir lote</Button></div>)}</div></section>}
        <fieldset className="rounded-xl border p-3">
          <legend className="px-1 text-sm font-semibold">Documentos que incluir</legend>
          <div className="flex flex-wrap gap-5 text-sm">
            {([["CONTRACT", "Contratos"], ["EPP", "EPP / seguridad"]] as const).map(([kind, label]) => <label className="flex items-center gap-2" key={kind}>
              <input checked={kinds.includes(kind)} className="h-4 w-4 accent-emerald-700" onChange={() => toggleKind(kind)} type="checkbox"/>{label}
            </label>)}
          </div>
        </fieldset>
        <div className="rounded-xl border">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b bg-slate-50 px-3 py-2 text-sm">
            <span className="font-semibold">Trabajadores ({selected.size} de {people.length})</span>
            <div className="flex gap-2"><Button size="sm" variant="ghost" onClick={() => setSelected(new Set(people.map((person) => person.personId)))}>Seleccionar todos</Button><Button size="sm" variant="ghost" onClick={() => setSelected(new Set())}>Limpiar</Button></div>
          </div>
          <div className="max-h-64 divide-y overflow-y-auto">
            {people.map((person) => <label className="flex cursor-pointer items-center gap-3 px-3 py-2.5 text-sm hover:bg-slate-50" key={person.personId}>
              <input checked={selected.has(person.personId)} className="h-4 w-4 accent-emerald-700" onChange={(event) => setSelected((current) => { const next = new Set(current); event.target.checked ? next.add(person.personId) : next.delete(person.personId); return next; })} type="checkbox"/>
              <span>{person.name}<span className="ml-2 text-xs text-slate-500">{person.rut}</span></span>
            </label>)}
          </div>
        </div>
        <p className="rounded-lg bg-sky-50 p-3 text-xs text-sky-900">Se incluirán las versiones vigentes en borrador o listas. Al generar el lote, esas versiones quedan reservadas para firma en papel y no podrán enviarse ni editarse electrónicamente. Si luego necesitas cambiar de modalidad o corregir datos, crea una nueva versión. Los lotes guardados se pueden reimprimir.</p>
        {error ? <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800" role="alert">{error}</p> : null}
        <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cerrar</Button><Button disabled={busy || !selected.size || !kinds.length || selected.size > 200} onClick={() => void prepare()}><Printer className="h-4 w-4"/>{busy ? "Preparando PDF…" : "Crear lote para firma en papel"}</Button></div>
        {selected.size > 200 ? <p className="text-right text-xs text-amber-800">El lote admite hasta 200 trabajadores. Desmarca algunos y prepara el siguiente lote después.</p> : null}
      </> : <>
        <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-950">
          <span>Listo para revisar: <strong>{stats?.documents} documentos</strong> · <strong>{stats?.pages} páginas</strong></span>
          <div className="flex flex-wrap gap-2"><Button size="sm" variant="secondary" onClick={() => { setPdfUrl(""); setStats(null); }} type="button">Volver</Button><Button size="sm" variant="secondary" onClick={downloadPdf}><Download className="h-4 w-4"/>Descargar PDF</Button><Button size="sm" onClick={() => frame.current?.contentWindow?.print()}><Printer className="h-4 w-4"/>Abrir impresión</Button></div>
        </div>
        <iframe ref={frame} className="h-[62vh] w-full rounded-lg border bg-slate-100" title="Vista previa del lote para firma en papel" src={pdfUrl}/>
      </>}
    </div>
  </ModalShell>;
}
