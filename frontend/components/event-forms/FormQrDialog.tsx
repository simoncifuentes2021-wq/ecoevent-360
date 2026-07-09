"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { QrCode } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { CopyPublicLinkButton } from "@/components/event-forms/CopyPublicLinkButton";
import { FormQrList } from "@/components/event-forms/FormQrList";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api";
import { createFormQrCode, deleteFormQrCode, getFormQrCodes } from "@/lib/api/formQr";
import type { EventForm } from "@/types/eventForm";
import type { FormQrCode } from "@/types/formQr";

const languageNames: Record<string, string> = {
  es: "Español",
  en: "English",
  pt: "Português",
  ko: "한국어"
};

export function FormQrDialog({ form, canCreate = true, canDelete, onClose }: { form: EventForm; canCreate?: boolean; canDelete: boolean; onClose: () => void }) {
  const [items, setItems] = useState<FormQrCode[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const baseUrl = useMemo(() => (typeof window === "undefined" ? "" : window.location.origin), []);
  const publicUrl = `${baseUrl}/f/${form.public_slug}`;
  const languages = form.available_languages?.length ? form.available_languages : [form.default_language || "es"];

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await getFormQrCodes(form.id));
    } catch (err) {
      setError(qrErrorMessage(err, "No se pudieron cargar los QR."));
    } finally {
      setLoading(false);
    }
  }, [form.id]);

  useEffect(() => { void load(); }, [load]);

  async function generateGeneral(force = false) {
    setSaving("FORM");
    setError(null);
    try {
      await createFormQrCode(form.id, { label: `QR ${form.title}`, qr_type: "FORM", force });
      await load();
    } catch (err) {
      setError(qrErrorMessage(err, "No se pudo generar el QR."));
    } finally {
      setSaving(null);
    }
  }

  async function generateLanguage(language: string, force = false) {
    setSaving(language);
    setError(null);
    try {
      await createFormQrCode(form.id, { label: `QR ${form.title} ${language.toUpperCase()}`, qr_type: "FORM_LANGUAGE", language, force });
      await load();
    } catch (err) {
      setError(qrErrorMessage(err, "No se pudo generar el QR."));
    } finally {
      setSaving(null);
    }
  }

  async function remove(qr: FormQrCode) {
    setSaving(qr.id);
    setError(null);
    try {
      await deleteFormQrCode(qr.id);
      await load();
    } catch (err) {
      setError(qrErrorMessage(err, "No se pudo eliminar el QR."));
    } finally {
      setSaving(null);
    }
  }

  return (
    <ModalShell title={`QR: ${form.title}`} description="Genera y descarga códigos QR para el formulario público." size="lg" onClose={onClose}>
      <div className="space-y-4">
        <section className="rounded-lg border bg-slate-50 p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-bold text-slate-950">QR general</p>
              <p className="break-all text-xs text-slate-600">{publicUrl}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <CopyPublicLinkButton url={publicUrl} />
              {canCreate ? (
                <Button disabled={Boolean(saving)} type="button" onClick={() => generateGeneral(true)}>
                  <QrCode className="h-4 w-4" />
                  {saving === "FORM" ? "Generando..." : "Generar QR"}
                </Button>
              ) : null}
            </div>
          </div>
        </section>

        {languages.length > 1 ? (
          <section className="rounded-lg border bg-white p-4">
            <p className="text-sm font-bold text-slate-950">QR por idioma</p>
            <div className="mt-3 grid gap-2 md:grid-cols-2">
              {languages.map((language) => {
                const url = `${publicUrl}?lang=${encodeURIComponent(language)}`;
                return (
                  <div className="rounded-lg border bg-slate-50 p-3" key={language}>
                    <p className="font-semibold text-slate-900">{languageNames[language] ?? language.toUpperCase()}</p>
                    <p className="mt-1 break-all text-xs text-slate-600">{url}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <CopyPublicLinkButton label="Copiar" url={url} />
                      {canCreate ? (
                        <Button disabled={Boolean(saving)} size="sm" type="button" onClick={() => generateLanguage(language, true)}>
                          <QrCode className="h-4 w-4" />
                          {saving === language ? "Generando..." : "Generar"}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ) : null}

        {error ? <ErrorState message={error} /> : null}
        {loading ? <LoadingState label="Cargando QR..." /> : <FormQrList canDelete={canDelete} items={items} onDelete={remove} />}
      </div>
    </ModalShell>
  );
}

function qrErrorMessage(err: unknown, fallback: string) {
  if (err instanceof ApiError && err.status === 404) {
    return "El módulo QR no está disponible en el backend activo. Reinicia el backend y verifica que la migración esté aplicada.";
  }
  return err instanceof Error ? err.message : fallback;
}
