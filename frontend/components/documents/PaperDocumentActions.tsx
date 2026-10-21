"use client";

import { useRef, useState } from "react";
import { Archive, Check, Download, Printer, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/common/ToastProvider";
import { documentApi, type ManagedDocument } from "@/lib/api/documents";

const PAPER_STATUS: Record<string, string> = {
  PREPARED: "Papel · preparado", PRINTED: "Papel · impreso",
  SIGNED_RECEIVED: "Papel · firmado recibido", ARCHIVED: "Papel · copia archivada",
};
const PAPER_STATUS_STYLE: Record<string, string> = {
  PREPARED: "bg-sky-100 text-sky-900",
  PRINTED: "bg-amber-100 text-amber-900",
  SIGNED_RECEIVED: "bg-emerald-100 text-emerald-900",
  ARCHIVED: "bg-violet-100 text-violet-900",
};

export function PaperDocumentActions({ document, onDone, allowPrepare = false }: { document: ManagedDocument; onDone: () => void; allowPrepare?: boolean }) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  const status = document.paper_status || "PREPARED";

  async function run(action: () => Promise<unknown>, success: string) {
    setBusy(true);
    try { await action(); toast({ title: success, tone: "success" }); onDone(); }
    catch (error) { toast({ title: "No se pudo completar la acción en papel", description: error instanceof Error ? error.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function upload(file?: File) {
    if (!file) return;
    await run(() => documentApi.uploadPaperSignedCopy(document.id, file), "Copia firmada archivada de forma privada");
    if (input.current) input.current.value = "";
  }

  async function viewCopy() {
    setBusy(true);
    try { const blob = await documentApi.paperSignedCopy(document.id); const url = URL.createObjectURL(blob); window.open(url, "_blank", "noopener,noreferrer"); window.setTimeout(() => URL.revokeObjectURL(url), 60_000); }
    catch (error) { toast({ title: "No se pudo abrir la copia archivada", description: error instanceof Error ? error.message : undefined, tone: "error" }); }
    finally { setBusy(false); }
  }

  async function printSingle() {
    const popup = window.open("about:blank", "_blank");
    if (!popup) {
      toast({ title: "Permite las ventanas emergentes para imprimir", tone: "error" });
      return;
    }
    popup.document.title = "Preparando documento para imprimir…";
    popup.document.body.textContent = "Preparando el PDF para impresión…";
    setBusy(true);
    try {
      const result = await documentApi.paperPrintSingle(document.id);
      const url = URL.createObjectURL(result.blob);
      popup.location.href = url;
      window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
      toast({ title: document.signature_method === "PAPER" ? "Documento listo para reimprimir" : "Documento preparado para firma en papel", tone: "success" });
      onDone();
    } catch (error) {
      popup.close();
      toast({ title: "No se pudo preparar la impresión", description: error instanceof Error ? error.message : undefined, tone: "error" });
    } finally { setBusy(false); }
  }

  return <div className="flex flex-wrap items-center gap-1.5">
    {document.signature_method === "PAPER" && <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${PAPER_STATUS_STYLE[status] || PAPER_STATUS_STYLE.PREPARED}`}>{PAPER_STATUS[status] || "Papel · preparado"}</span>}
    {(document.signature_method === "PAPER" || allowPrepare) && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void printSingle()}><Printer className="h-4 w-4"/>{document.signature_method === "PAPER" ? "Reimprimir documento" : "Imprimir este documento"}</Button>}
    {["PREPARED", "PRINTED"].includes(status) && document.signature_method === "PAPER" && <Button size="sm" disabled={busy} onClick={() => void run(() => documentApi.markPaperSignedReceived(document.id), "Firma en papel recibida") }><Check className="h-4 w-4"/>Registrar firma recibida</Button>}
    {["PRINTED", "SIGNED_RECEIVED", "ARCHIVED"].includes(status) && !document.paper_evidence_file_name && <><input ref={input} accept="application/pdf,image/png,image/jpeg" className="hidden" onChange={(event) => void upload(event.target.files?.[0])} type="file"/><Button size="sm" variant="secondary" disabled={busy} onClick={() => input.current?.click()}><Upload className="h-4 w-4"/>Adjuntar copia</Button></>}
    {document.paper_evidence_file_name && <Button size="sm" variant="secondary" disabled={busy} onClick={() => void viewCopy()}><Download className="h-4 w-4"/><Archive className="h-4 w-4"/>Copia archivada</Button>}
  </div>;
}
