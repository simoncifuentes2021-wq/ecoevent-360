"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, ExternalLink, LoaderCircle, ShieldCheck } from "lucide-react";

import { publicPreview, documentApi } from "@/lib/api/documents";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SignaturePad } from "@/components/documents/SignaturePad";

type PublicDocument = {
  id: string; title: string; kind: string; person_name: string;
  snapshot: Record<string, unknown>; status: string; worker_signed: boolean; worker_email?: string | null; electronic_consent_text?: string; electronic_consent_version?: string; signed_copy_email_sent?: boolean; signed_copy_email_error?: string | null; worker_form_data?: { riohs_received?: boolean; eirl_completed?: boolean; items_reviewed?: boolean; received_item_codes?: string[]; confirmed_at?: string } | null; signature_notice: string;
};

export function PublicDocumentPortal() {
  const [tokens, setTokens] = useState<string[]>([]);
  const [activeDocumentIndex, setActiveDocumentIndex] = useState(0);
  const token = tokens[activeDocumentIndex] || "";
  const [rut, setRut] = useState("");
  const [documents, setDocuments] = useState<Array<PublicDocument | null>>([]);
  const document = documents[activeDocumentIndex] || null;
  const [workerName, setWorkerName] = useState("");
  const [accepted, setAccepted] = useState(false);
  const [electronicConsent, setElectronicConsent] = useState(false);
  const [deliveryError, setDeliveryError] = useState("");
  const [emailSent, setEmailSent] = useState(false);
  const [eppAcknowledgments, setEppAcknowledgments] = useState({ riohs_received: true, eirl_completed: true, items_reviewed: false, received_item_codes: [] as string[] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [pdfUrl, setPdfUrl] = useState("");
  const [workerSignature, setWorkerSignature] = useState("");

  useEffect(() => {
    const secret = window.location.hash.slice(1);
    if (secret) {
      const bundle = secret.split(".");
      setTokens(bundle[0] === "bundle" && bundle.length === 3 ? bundle.slice(1) : [secret]);
      window.history.replaceState(null, "", window.location.pathname);
    }
  }, []);
  useEffect(() => () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl); }, [pdfUrl]);

  async function validateIdentity(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const opened = await Promise.all(tokens.map(async (documentToken) =>
        await documentApi.publicOpen(documentToken, rut) as unknown as PublicDocument
      ));
      setDocuments(opened);
      setEmailSent(Boolean(opened[0]?.signed_copy_email_sent));
      setDeliveryError(opened[0]?.signed_copy_email_error || "");
      setWorkerName(opened[0]?.person_name || "");
      const eppDocument = opened.find((item) => item.kind === "EPP");
      const eppSnapshot = eppDocument?.snapshot.epp as { items?: Array<{ item_code: string }> } | undefined;
      setEppAcknowledgments({
        riohs_received: eppDocument?.worker_signed ? Boolean(eppDocument.worker_form_data?.riohs_received) : true,
        eirl_completed: eppDocument?.worker_signed ? Boolean(eppDocument.worker_form_data?.eirl_completed) : true,
        items_reviewed: Boolean(eppDocument?.worker_form_data?.items_reviewed),
        received_item_codes: eppDocument?.worker_form_data?.received_item_codes || eppSnapshot?.items?.map((item) => item.item_code) || [],
      });
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo validar la identidad."); }
    finally { setBusy(false); }
  }

  async function reviewPdf() {
    setBusy(true); setError("");
    try {
      const blob = await publicPreview(token, rut);
      if (pdfUrl) URL.revokeObjectURL(pdfUrl);
      setPdfUrl(URL.createObjectURL(blob));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo abrir el documento."); }
    finally { setBusy(false); }
  }

  async function sign() {
    if (!electronicConsent) { setError("Debes aceptar expresamente la gestión y firma electrónica."); return; }
    if (document?.kind === "EPP" && !eppAcknowledgmentsComplete) { setError("Completa las constancias de recepción de RIOHS, EIRL y los elementos entregados."); return; }
    setBusy(true); setError("");
    try {
      const result = await documentApi.publicSign(token, rut, workerName, workerSignature, accepted, electronicConsent, document?.kind === "EPP" ? eppAcknowledgments : undefined);
      setDocuments((current) => current.map((item, index) => index === activeDocumentIndex && item
        ? { ...item, status: result.status, worker_signed: true, worker_form_data: document?.kind === "EPP" ? eppAcknowledgments : item.worker_form_data }
        : item));
      setEmailSent(result.email_sent);
      setDeliveryError(result.delivery_error || "");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudo registrar la confirmación."); }
    finally { setBusy(false); }
  }

  const snapshot = document?.snapshot || {};
  const person = (snapshot.person || {}) as Record<string, unknown>;
  const employment = (snapshot.employment || {}) as Record<string, unknown>;
  const event = (snapshot.event || {}) as Record<string, unknown>;
  const snapshotEpp = (snapshot.epp || {}) as Record<string, unknown>;
  const workerConfirmedCodes = new Set(document?.worker_form_data?.received_item_codes || []);
  const workerConfirmedDate = document?.worker_form_data?.confirmed_at?.slice(0, 10) || null;
  const epp = { ...snapshotEpp, riohs_received: Boolean(document?.worker_form_data?.riohs_received), eirl_completed: Boolean(document?.worker_form_data?.eirl_completed) };
  const eppItems: Array<Record<string, unknown>> = (Array.isArray(snapshotEpp.items) ? snapshotEpp.items as Array<Record<string, unknown>> : []).map((item): Record<string, unknown> => ({
    ...item,
    received_at: document?.worker_signed && workerConfirmedCodes.has(String(item.item_code)) ? workerConfirmedDate : null,
    received_conformity: document?.worker_signed && workerConfirmedCodes.has(String(item.item_code)),
  }));
  const availableEppItems = eppItems;
  const deliveredEppItems = availableEppItems;
  const requiresRiohsAck = true;
  const requiresEirlAck = true;
  const eppAcknowledgmentsComplete = eppAcknowledgments.riohs_received && eppAcknowledgments.eirl_completed && eppAcknowledgments.items_reviewed;

  return <main className="min-h-screen bg-slate-50 px-4 py-8 sm:py-14">
    <div className="mx-auto max-w-3xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-lg">
      <div className="bg-emerald-900 px-6 py-7 text-white sm:px-9"><p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-200">Greenway App · Portal seguro</p><h1 className="mt-2 text-2xl font-bold">Revisión de documentos</h1><p className="mt-1 text-sm text-emerald-100">Acceso limitado al documento compartido contigo.</p></div>
      <div className="space-y-6 p-6 sm:p-9">
        {tokens.length > 1 && <nav aria-label="Documentos de la faena" className="grid grid-cols-2 gap-2 rounded-xl bg-slate-100 p-1">{["Contrato", "Registro EPP / Seguridad"].map((label, index) => <button type="button" key={label} onClick={() => { setActiveDocumentIndex(index); setPdfUrl(""); setError(""); setAccepted(false); setElectronicConsent(false); setWorkerSignature(""); setEmailSent(Boolean(documents[index]?.signed_copy_email_sent)); setDeliveryError(documents[index]?.signed_copy_email_error || ""); }} className={`rounded-lg px-3 py-2 text-sm font-semibold ${index === activeDocumentIndex ? "bg-white text-emerald-800 shadow-sm" : "text-slate-600"}`}>{label}</button>)}</nav>}
        {!tokens.length ? <div className="rounded-lg bg-amber-50 p-4 text-sm text-amber-900">El enlace no contiene una credencial válida. Solicita un nuevo enlace a tu supervisor.</div> : !document ? <form className="space-y-4" onSubmit={(event) => void validateIdentity(event)}><div><h2 className="text-lg font-semibold">Validar identidad</h2><p className="mt-1 text-sm text-slate-600">Ingresa tu RUT una sola vez para abrir todos los documentos de esta faena.</p></div><label className="grid gap-1.5 text-sm font-medium">RUT<Input autoComplete="off" maxLength={16} required value={rut} onChange={(event) => setRut(event.target.value)} placeholder="12.345.678-5"/></label>{error && <p role="alert" className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800">{error}</p>}<Button disabled={busy || !token}>{busy && <LoaderCircle className="h-4 w-4 animate-spin"/>}{busy ? "Validando…" : "Continuar"}</Button></form> : <>
          <section><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-wide text-emerald-800">{document.kind === "CONTRACT" ? "Contrato por obra o faena" : "Registro EPP / Seguridad"}</p><h2 className="mt-1 text-xl font-bold text-slate-900">{document.title}</h2><p className="mt-1 text-sm text-slate-600">{document.person_name}</p></div><span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">{document.worker_signed ? "Firmado" : "Pendiente de revisión"}</span></div></section>
          {document.kind === "CONTRACT" ? <dl className="grid gap-x-8 gap-y-3 rounded-xl border bg-slate-50 p-4 sm:grid-cols-2">{[["Cargo", employment.position], ["Área", employment.area], ["Inicio", employment.start_date], ["Término", employment.end_date], ["Evento", event.name || "Global"], ["Lugar de trabajo", employment.workplace || event.venue || event.address], ["Remuneración", employment.remuneration]].map(([label, value]) => <div key={String(label)}><dt className="text-xs font-semibold uppercase text-slate-500">{String(label)}</dt><dd className="mt-1 text-sm font-medium text-slate-900">{value ? String(value) : "—"}</dd></div>)}</dl> : <section className="space-y-3"><div className="grid gap-3 sm:grid-cols-2"><div className="rounded-lg border p-3"><p className="text-xs text-slate-500">RIOHS</p><p className="mt-1 font-semibold">{epp.riohs_received ? "Recepción registrada" : "Pendiente"}</p></div><div className="rounded-lg border p-3"><p className="text-xs text-slate-500">EIRL</p><p className="mt-1 font-semibold">{epp.eirl_completed ? "Evaluación registrada" : "Pendiente"}</p></div></div><div className="overflow-x-auto rounded-xl border"><table className="w-full text-sm"><thead className="bg-slate-50 text-left text-xs uppercase text-slate-500"><tr><th className="p-3">Elemento</th><th className="p-3">Recepción</th><th className="p-3">Recibido conforme</th></tr></thead><tbody>{eppItems.map((item) => <tr className="border-t" key={String(item.item_code)}><td className="p-3">{String(item.label)}</td><td className="p-3">{String(item.received_at || "—")}</td><td className="p-3">{item.received_conformity ? "Sí" : "No"}</td></tr>)}</tbody></table></div></section>}
          <Button variant="secondary" disabled={busy} onClick={() => void reviewPdf()}><ExternalLink className="h-4 w-4"/> Revisar documento PDF</Button>
          {document.kind === "EPP" && !document.worker_signed && <section className="space-y-3 rounded-xl border border-sky-200 bg-sky-50/60 p-4"><div><h3 className="font-semibold text-slate-900">Constancia de recepción</h3><p className="mt-1 text-sm text-slate-600">El empleador declara entregados el RIOHS, la información EIRL y todos los elementos de la lista. Revisa el PDF; luego podrás confirmar y firmar todo en un solo paso.</p></div>{requiresRiohsAck && <label className="flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" checked={eppAcknowledgments.riohs_received} disabled aria-label="RIOHS entregado por el empleador"/><span>Entregado por el empleador: <strong>RIOHS</strong></span></label>}{requiresEirlAck && <label className="flex items-start gap-2 text-sm"><input className="mt-1" type="checkbox" checked={eppAcknowledgments.eirl_completed} disabled aria-label="Información EIRL entregada por el empleador"/><span>Entregado por el empleador: <strong>Información EIRL</strong></span></label>}{deliveredEppItems.map((item) => { const code = String(item.item_code); return <label className="flex items-start gap-2 text-sm" key={code}><input className="mt-1" type="checkbox" checked={eppAcknowledgments.received_item_codes.includes(code)} disabled aria-label={`Entregado: ${String(item.label)}`}/><span>Entregado por el empleador: <strong>{String(item.label)}</strong></span></label>; })}<label className="flex items-start gap-2 border-t border-sky-200 pt-3 text-sm font-medium"><input className="mt-1" type="checkbox" checked={eppAcknowledgments.items_reviewed} disabled={!pdfUrl} onChange={(event) => setEppAcknowledgments((old) => ({ ...old, items_reviewed: event.target.checked }))}/><span>Confirmo que leí el documento y que recibí conforme el RIOHS, la información EIRL y todos los elementos EPP indicados.</span></label></section>}
          {pdfUrl && <iframe className="h-[55vh] w-full rounded-xl border" title="Documento PDF para revisión" src={pdfUrl}/>}
          {document.worker_signed ? <div className="flex items-start gap-3 rounded-xl bg-emerald-50 p-4 text-emerald-900"><CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0"/><div><p className="font-semibold">Documento firmado y finalizado.</p>{emailSent ? <p className="mt-1 text-sm">La copia final se envió a {document.worker_email || "tu correo personal registrado"}.</p> : <p className="mt-1 text-sm">{deliveryError || "La firma quedó registrada. Si no recibes la copia en tu correo personal, contacta a tu supervisor."}</p>}<p className="mt-1 text-sm">{document.signature_notice}</p></div></div> : <section className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/60 p-4"><label className="grid gap-1.5 text-sm font-medium">Confirma tu nombre<Input autoComplete="name" required value={workerName} onChange={(event) => setWorkerName(event.target.value)}/></label><label className="flex items-start gap-2 text-sm text-slate-700"><input className="mt-1" type="checkbox" checked={accepted} disabled={!pdfUrl} onChange={(event) => setAccepted(event.target.checked)}/><span>Confirmo que revisé el documento mostrado y que los datos son correctos.</span></label><div className="rounded-lg border border-emerald-200 bg-white p-3"><label className="flex items-start gap-2 text-sm font-medium text-slate-800"><input className="mt-1" type="checkbox" checked={electronicConsent} disabled={!pdfUrl} onChange={(event) => setElectronicConsent(event.target.checked)}/><span>{document.electronic_consent_text || `Acepto expresamente que el documento se gestione, firme y remita por medios electrónicos. La copia final se enviará a mi correo personal registrado: ${document.worker_email || "no informado"}. Entiendo que puedo solicitar la modalidad en papel si no acepto este procedimiento.`}</span></label><p className="mt-2 pl-6 text-xs text-slate-500">Correo personal registrado: <strong>{document.worker_email || "No informado"}</strong></p></div><SignaturePad onChange={setWorkerSignature} disabled={!pdfUrl || busy} label="Firma del trabajador"/>{error && <p role="alert" className="rounded-lg bg-rose-100 p-3 text-sm text-rose-800">{error}</p>}<Button disabled={busy || !accepted || !electronicConsent || !pdfUrl || !workerSignature} onClick={() => void sign()}>{busy && <LoaderCircle className="h-4 w-4 animate-spin"/>}Firmar y finalizar documento</Button><p className="text-xs text-slate-600">Si no aceptas el trámite electrónico, no firmes aquí y solicita a tu supervisor la modalidad en papel.</p></section>}
          <div className="flex items-start gap-2 rounded-lg border border-slate-200 p-3 text-xs text-slate-600"><ShieldCheck className="h-4 w-4 shrink-0 text-emerald-700"/><p>Se registran la aceptación, fecha y hora del servidor, versión del documento y evidencia técnica básica. La firma dibujada no es firma electrónica avanzada ni está certificada por un proveedor.</p></div>
        </>}
      </div>
    </div>
  </main>;
}
