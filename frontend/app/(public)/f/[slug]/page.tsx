"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarX } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { LanguageSelectionScreen } from "@/components/public-forms/LanguageSelectionScreen";
import { PublicFormHeader } from "@/components/public-forms/PublicFormHeader";
import { PublicFormRenderer } from "@/components/public-forms/PublicFormRenderer";
import { getPublicForm } from "@/lib/api/publicForms";
import type { PublicEventForm } from "@/types/eventForm";

export default function PublicFormPage({ params }: { params: { slug: string } }) {
  const searchParams = useSearchParams();
  const [form, setForm] = useState<PublicEventForm | null>(null);
  const [language, setLanguage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (lang?: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPublicForm(params.slug, lang);
      setForm(data);
      if (data.language) setLanguage(data.language);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el formulario.");
    } finally {
      setLoading(false);
    }
  }, [params.slug]);

  useEffect(() => { void load(searchParams.get("lang")); }, [load, searchParams]);

  async function selectLanguage(lang: string) {
    setLanguage(lang);
    const url = new URL(window.location.href);
    url.searchParams.set("lang", lang);
    window.history.replaceState(null, "", url.toString());
    await load(lang);
  }

  if (loading) return <LoadingState label="Cargando formulario..." />;
  if (error || !form) {
    return <UnavailableFormScreen message={publicUnavailableMessage(error)} onRetry={() => load(language)} />;
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <PublicFormHeader form={form} />
      {form.needs_language_selection && !language ? <LanguageSelectionScreen form={form} onSelect={selectLanguage} /> : <PublicFormRenderer form={form} language={language || form.default_language} />}
    </div>
  );
}

function UnavailableFormScreen({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-100 px-4 py-10">
      <section className="w-full max-w-lg rounded-lg border bg-white p-6 text-center shadow-xl">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-slate-100 text-slate-700">
          <CalendarX className="h-7 w-7" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-slate-950">Formulario no disponible</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{message}</p>
        <button
          className="mt-5 rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800"
          type="button"
          onClick={onRetry}
        >
          Reintentar
        </button>
      </section>
    </main>
  );
}

function publicUnavailableMessage(error: string | null) {
  if (error === "Form is not active") return "Este formulario no está abierto para recibir respuestas en este momento.";
  if (error === "Form is not open yet") return "Este formulario todavía no está abierto. Intenta nuevamente cuando comience el periodo de respuestas.";
  if (error === "Form is closed") return "Este formulario ya cerró y no acepta nuevas respuestas.";
  if (error === "Form not found") return "El enlace no corresponde a un formulario público disponible.";
  return "No pudimos cargar este formulario. Revisa el enlace o intenta nuevamente más tarde.";
}
