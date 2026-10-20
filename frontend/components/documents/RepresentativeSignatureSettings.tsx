"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import { CheckCircle2, LoaderCircle, PenLine, ShieldCheck } from "lucide-react";

import { SignaturePad } from "@/components/documents/SignaturePad";
import { Button } from "@/components/ui/button";
import { documentApi, type RepresentativeSignatureProfile } from "@/lib/api/documents";

export function RepresentativeSignatureSettings({
  representativeName,
  representativeRut,
  toast,
}: {
  representativeName: string;
  representativeRut: string;
  toast: (notice: { title: string; description?: string; tone: "success" | "error" }) => void;
}) {
  const [profile, setProfile] = useState<RepresentativeSignatureProfile | null>(null);
  const [signature, setSignature] = useState("");
  const [authorized, setAuthorized] = useState(false);
  const [signaturePadResetToken, setSignaturePadResetToken] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    void documentApi.representativeSignature()
      .then((result) => { if (active) setProfile(result); })
      .catch((cause) => {
        if (active) toast({ title: "No se pudo cargar la firma del representante", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [toast]);

  async function save() {
    if (!signature) return;
    setSaving(true);
    try {
      const result = await documentApi.saveRepresentativeSignature(signature);
      setProfile(result);
      setSignature("");
      setAuthorized(false);
      setSignaturePadResetToken((current) => current + 1);
      toast({ title: "Firma del representante guardada", description: "Se reutilizará al autorizar cada envío. Cada PDF conservará la firma aplicada a su propia versión.", tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudo guardar la firma", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setSaving(false); }
  }

  async function remove() {
    if (!window.confirm("¿Eliminar la firma reutilizable? Los documentos ya enviados conservarán la firma congelada en su versión.")) return;
    setSaving(true);
    try {
      setProfile(await documentApi.deleteRepresentativeSignature());
      setSignature("");
      setAuthorized(false);
      setSignaturePadResetToken((current) => current + 1);
      toast({ title: "Firma reutilizable eliminada", description: "Los documentos ya emitidos no se modificaron.", tone: "success" });
    } catch (cause) {
      toast({ title: "No se pudo eliminar la firma", description: cause instanceof Error ? cause.message : undefined, tone: "error" });
    } finally { setSaving(false); }
  }

  return <details className="rounded-xl border border-violet-200 bg-white p-4 shadow-sm">
    <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold text-slate-900"><PenLine className="h-4 w-4 text-violet-700"/>Firma reutilizable del representante legal</summary>
    <p className="mt-2 text-sm text-slate-600">Regístrala una sola vez dibujándola. Al confirmar cada envío se aplicará al PDF congelado de esa versión; no se insertará en documentos sin tu autorización de envío.</p>
    <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-950"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0"/><p>Esta firma dibujada no es firma electrónica avanzada ni incluye certificación de un proveedor. La aplicación conserva el PDF y su trazabilidad; valida con asesoría laboral el uso que corresponde a cada documento.</p></div>
    <div className="mt-4 grid gap-3 rounded-lg bg-slate-50 p-3 text-sm sm:grid-cols-2"><p><span className="text-slate-500">Representante configurado</span><strong className="mt-0.5 block">{representativeName || "Completa primero los datos base"}</strong></p><p><span className="text-slate-500">RUT</span><strong className="mt-0.5 block">{representativeRut || "—"}</strong></p></div>
    {loading ? <div className="mt-4 flex items-center gap-2 text-sm text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin"/>Cargando configuración…</div> : profile?.configured ? <div className="mt-4 flex flex-wrap items-center gap-4 rounded-lg border border-emerald-200 bg-emerald-50/50 p-3"><Image unoptimized className="h-16 w-52 rounded border bg-white object-contain p-2" src={profile.signature_data_url || ""} alt="Firma guardada del representante" width={208} height={64}/><div className="text-sm"><p className="flex items-center gap-1 font-semibold text-emerald-900"><CheckCircle2 className="h-4 w-4"/>Firma registrada</p><p className="text-slate-600">{profile.signer_name} · {profile.signer_rut}</p><p className="text-xs text-slate-500">Dibuja una nueva para reemplazarla.</p></div></div> : <p className="mt-4 rounded-lg border border-dashed p-3 text-sm text-slate-600">Aún no hay una firma reutilizable. Debe corresponder al representante y RUT guardados arriba.</p>}
    <div className="mt-4 space-y-3"><SignaturePad resetToken={signaturePadResetToken} onChange={setSignature} disabled={saving || !representativeName || !representativeRut} label={profile?.configured ? "Dibuja la nueva firma para reemplazarla" : "Dibuja la firma del representante"}/><label className="flex items-start gap-2 rounded-lg border border-slate-200 p-3 text-sm text-slate-700"><input className="mt-1" type="checkbox" checked={authorized} disabled={saving || !signature} onChange={(event) => setAuthorized(event.target.checked)}/><span>Confirmo que cuento con autorización del representante legal para registrar y reutilizar esta firma en los documentos cuyo envío apruebe.</span></label><div className="flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" disabled={saving || !profile?.configured} onClick={() => void remove()}>Eliminar firma guardada</Button><Button type="button" disabled={saving || !signature || !authorized || !representativeName || !representativeRut} onClick={() => void save()}>{saving ? "Guardando…" : profile?.configured ? "Reemplazar firma" : "Guardar firma reutilizable"}</Button></div></div>
  </details>;
}
