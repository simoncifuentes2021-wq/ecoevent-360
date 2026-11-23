"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, FileCheck2, LoaderCircle, Save } from "lucide-react";
import { SignaturePad } from "@/components/documents/SignaturePad";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { DisposalCertificateDefaults } from "@/types/disposal-certificate";

const EMPTY: DisposalCertificateDefaults = {
  issuer_name: "",
  issuer_rut: "",
  issuer_address: "",
  introduction_template: "",
  treatment_description: "",
  closing_text: "",
  director_name: "",
  director_role: "Director Greenway",
  director_email: "",
  director_phone: "",
  signature_data_url: "",
};

export function DisposalCertificateDefaultsSettings() {
  const [defaults, setDefaults] = useState<DisposalCertificateDefaults>(EMPTY);
  const [signatureDraft, setSignatureDraft] = useState("");
  const [signatureTouched, setSignatureTouched] = useState(false);
  const [authorized, setAuthorized] = useState(false);
  const [resetPad, setResetPad] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    void api.get<DisposalCertificateDefaults>("/disposal-certificates/defaults")
      .then((value) => { if (active) setDefaults(value); })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "No se pudieron cargar los datos del certificado."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  function setField(key: keyof DisposalCertificateDefaults, value: string) {
    setDefaults((current) => ({ ...current, [key]: value }));
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (signatureTouched && signatureDraft && !authorized) {
      setError("Confirma que tienes autorización para registrar la firma del director.");
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const payload = {
        ...defaults,
        signature_data_url: signatureTouched ? signatureDraft : defaults.signature_data_url,
      };
      const updated = await api.put<DisposalCertificateDefaults>("/disposal-certificates/defaults", payload);
      setDefaults(updated);
      setSignatureDraft("");
      setSignatureTouched(false);
      setAuthorized(false);
      setResetPad((value) => value + 1);
      setNotice("Datos guardados para los próximos certificados.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "No se pudieron guardar los datos del certificado.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <details className="rounded-xl border border-emerald-200 bg-white p-4 shadow-sm">
      <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold text-slate-900">
        <FileCheck2 className="h-4 w-4 text-emerald-700" />
        Datos base de Greenway para certificados de disposición final
      </summary>
      <p className="mt-2 text-sm text-slate-600">
        Guarda una vez los datos de Greenway y del director. Se usarán al emitir certificados. Esta configuración es independiente: editarla aquí no cambia los datos ni la firma de los contratos.
      </p>
      {loading ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-slate-500"><LoaderCircle className="h-4 w-4 animate-spin" />Cargando configuración…</div>
      ) : (
        <form className="mt-4 space-y-5" onSubmit={(event) => void save(event)}>
          <section>
            <h3 className="mb-3 font-semibold text-slate-900">Empresa emisora</h3>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {([
                ["issuer_name", "Razón social de Greenway"],
                ["issuer_rut", "RUT de Greenway"],
                ["issuer_address", "Dirección que aparecerá en el certificado"],
              ] as Array<[keyof DisposalCertificateDefaults, string]>).map(([key, label]) => (
                <label className="grid gap-1.5 text-sm font-medium text-slate-700" key={key}>
                  {label}
                  <Input required value={defaults[key]} onChange={(event) => setField(key, event.target.value)} />
                </label>
              ))}
            </div>
            <p className="mt-2 text-xs text-slate-500">Se precargan desde los datos base actuales de Greenway. Al guardarlos para este certificado quedan separados de la configuración de contratos.</p>
          </section>
          <section>
            <h3 className="mb-3 font-semibold text-slate-900">Texto del certificado</h3>
            <div className="grid gap-3">
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Introducción
                <textarea required rows={4} maxLength={1600} className="rounded-lg border border-slate-300 p-3" value={defaults.introduction_template} onChange={(event) => setField("introduction_template", event.target.value)} />
                <span className="text-xs font-normal text-slate-500">Variables: {"{issuer_name}"}, {"{issuer_rut}"}, {"{issuer_address}"}, {"{recipient_name}"}, {"{recipient_rut}"}, {"{event_name}"}.</span>
              </label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Texto permanente de disposición final
                <textarea required rows={4} maxLength={1200} className="rounded-lg border border-slate-300 p-3" value={defaults.treatment_description} onChange={(event) => setField("treatment_description", event.target.value)} />
              </label>
              <label className="grid gap-1.5 text-sm font-medium text-slate-700">Cierre
                <textarea rows={2} maxLength={600} className="rounded-lg border border-slate-300 p-3" value={defaults.closing_text} onChange={(event) => setField("closing_text", event.target.value)} />
              </label>
            </div>
          </section>
          <section>
            <h3 className="mb-3 font-semibold text-slate-900">Director y firma</h3>
            <div className="mb-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {([
                ["director_name", "Nombre del director"],
                ["director_role", "Cargo que se mostrará"],
                ["director_email", "Correo de contacto"],
                ["director_phone", "Teléfono de contacto"],
              ] as Array<[keyof DisposalCertificateDefaults, string]>).map(([key, label]) => (
                <label className="grid gap-1.5 text-sm font-medium text-slate-700" key={key}>
                  {label}
                  <Input required value={defaults[key]} onChange={(event) => setField(key, event.target.value)} />
                </label>
              ))}
            </div>
            {defaults.signature_data_url && !signatureDraft ? (
              <div className="mb-3 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
                <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-emerald-900"><CheckCircle2 className="h-4 w-4" />Firma registrada para certificados</p>
                <img className="h-20 w-64 rounded border bg-white object-contain p-2" src={defaults.signature_data_url} alt="Firma guardada para certificados" />
                <p className="mt-2 text-xs text-slate-600">Si ya había una firma del director en Documentos, se usa como punto de partida. Al guardarla aquí queda separada; los cambios de esta sección no modifican la firma de contratos.</p>
              </div>
            ) : null}
            <SignaturePad
              resetToken={resetPad}
              label={defaults.signature_data_url ? "Dibuja una firma nueva para reemplazarla" : "Dibuja la firma del director"}
              disabled={saving}
              onChange={(value) => { setSignatureDraft(value); setSignatureTouched(true); setAuthorized(false); }}
            />
            {signatureTouched && signatureDraft ? (
              <label className="mt-3 flex items-start gap-2 rounded-lg border border-slate-200 p-3 text-sm text-slate-700">
                <input className="mt-1" type="checkbox" checked={authorized} onChange={(event) => setAuthorized(event.target.checked)} />
                <span>Confirmo que cuento con autorización del director para guardar y utilizar esta firma en los certificados de disposición final.</span>
              </label>
            ) : null}
          </section>
          {error ? <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
          {notice ? <p role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</p> : null}
          <div className="flex justify-end"><Button disabled={saving || !defaults.issuer_name.trim() || !defaults.issuer_rut.trim() || !defaults.director_name.trim() || !defaults.treatment_description.trim() || (signatureTouched && !!signatureDraft && !authorized)}>{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{saving ? "Guardando…" : "Guardar datos del certificado"}</Button></div>
        </form>
      )}
    </details>
  );
}
