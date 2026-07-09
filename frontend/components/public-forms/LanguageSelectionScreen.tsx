"use client";

import type { PublicEventForm } from "@/types/eventForm";

const languageMeta: Record<string, { flag: string; label: string; native: string }> = {
  es: { flag: "ES", label: "Español", native: "Español" },
  en: { flag: "GB", label: "English", native: "English" },
  pt: { flag: "BR", label: "Português", native: "Português" },
  ko: { flag: "KR", label: "한국어", native: "한국어" }
};

export function LanguageSelectionScreen({ form, onSelect }: { form: PublicEventForm; onSelect: (lang: string) => void }) {
  const languages = form.available_languages?.length ? form.available_languages : ["es"];
  return (
    <main className="-mt-16 px-4 pb-12">
      <section className="mx-auto max-w-xl rounded-lg bg-white p-5 shadow-2xl md:p-7">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">{form.title}</p>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">Elige tu idioma para continuar</h2>
        </div>
        <div className="mt-6 grid gap-3">
          {languages.map((lang) => {
            const item = languageMeta[lang] ?? { flag: lang.toUpperCase(), label: lang.toUpperCase(), native: lang.toUpperCase() };
            return (
              <button
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-4 text-left shadow-sm transition hover:border-emerald-500 hover:bg-emerald-50"
                key={lang}
                onClick={() => onSelect(lang)}
                type="button"
              >
                <span className="flex items-center gap-3">
                  <span className="grid h-12 w-12 place-items-center rounded-md bg-slate-900 text-sm font-black text-white">{item.flag}</span>
                  <span>
                    <span className="block text-base font-bold text-slate-950">{item.label}</span>
                    <span className="block text-sm text-slate-500">{item.native}</span>
                  </span>
                </span>
                <span className="text-lg text-emerald-700">→</span>
              </button>
            );
          })}
        </div>
      </section>
    </main>
  );
}
