"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CalendarX } from "lucide-react";

import { LoadingState } from "@/components/common/LoadingState";
import { LanguageSelectionScreen } from "@/components/public-forms/LanguageSelectionScreen";
import { PublicFormHeader } from "@/components/public-forms/PublicFormHeader";
import { PublicFormRenderer } from "@/components/public-forms/PublicFormRenderer";
import { getPublicForm } from "@/lib/api/publicForms";
import { normalizePublicFormLanguage, publicFormCopy } from "@/lib/publicFormI18n";
import type { PublicEventForm } from "@/types/eventForm";

export function PublicFormPage({ slug }: { slug: string }) {
  const searchParams = useSearchParams();
  const [form, setForm] = useState<PublicEventForm | null>(null);
  const [language, setLanguage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestedLanguage = normalizePublicFormLanguage(language || searchParams.get("lang"));
  const copy = publicFormCopy(requestedLanguage);

  const load = useCallback(async (lang?: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPublicForm(slug, lang);
      setForm(data);
      if (data.language) setLanguage(data.language);
    } catch (err) {
      setError(err instanceof Error ? err.message : publicFormCopy(lang).loadError);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => { void load(searchParams.get("lang")); }, [load, searchParams]);

  async function selectLanguage(lang: string) {
    setLanguage(lang);
    const url = new URL(window.location.href);
    url.searchParams.set("lang", lang);
    window.history.replaceState(null, "", url.toString());
    await load(lang);
  }

  if (loading) return <LoadingState label={copy.loadingForm} />;
  if (error || !form) {
    return <UnavailableFormScreen language={requestedLanguage} message={publicUnavailableMessage(error, requestedLanguage)} onRetry={() => load(language || requestedLanguage)} />;
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <PublicFormHeader form={form} />
      {form.needs_language_selection && !language ? <LanguageSelectionScreen form={form} onSelect={selectLanguage} /> : <PublicFormRenderer form={form} language={language || form.default_language} />}
    </div>
  );
}

function UnavailableFormScreen({ message, language, onRetry }: { message: string; language: string; onRetry: () => void }) {
  const copy = publicFormCopy(language);
  return (
    <main className="grid min-h-screen place-items-center bg-slate-100 px-4 py-10">
      <section className="w-full max-w-lg rounded-lg border bg-white p-6 text-center shadow-xl">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-slate-100 text-slate-700">
          <CalendarX className="h-7 w-7" />
        </div>
        <h1 className="mt-4 text-2xl font-bold text-slate-950">{copy.unavailableTitle}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{message}</p>
        <button
          className="mt-5 rounded-md bg-slate-900 px-4 py-2 text-sm font-bold text-white transition hover:bg-slate-800"
          type="button"
          onClick={onRetry}
        >
          {copy.retry}
        </button>
      </section>
    </main>
  );
}

function publicUnavailableMessage(error: string | null, language: string) {
  const copy = publicFormCopy(language);
  if (error === "Form is not active") return copy.inactive;
  if (error === "Form is not open yet") return copy.notOpenYet;
  if (error === "Form is closed") return copy.closed;
  if (error === "Form not found") return copy.notFound;
  return copy.unavailableDefault;
}
