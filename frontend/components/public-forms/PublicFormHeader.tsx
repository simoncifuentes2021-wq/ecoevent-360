"use client";

import type { PublicEventForm } from "@/types/eventForm";

export function PublicFormHeader({ form }: { form: PublicEventForm }) {
  const banner = form.banner_url || "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=1800&q=80";
  return (
    <header className="relative min-h-[260px] overflow-hidden bg-slate-900 text-white">
      <img alt="" className="absolute inset-0 h-full w-full object-cover opacity-80" src={banner} />
      <div className="absolute inset-0 bg-gradient-to-b from-slate-950/35 via-slate-950/10 to-slate-950/70" />
      <div className="relative mx-auto flex min-h-[260px] max-w-5xl flex-col justify-between px-5 py-6">
        <div className="flex items-center gap-3">
          {form.primary_logo_url ? <img alt="Logo" className="h-14 max-w-[180px] rounded-md bg-white object-contain p-2 shadow-lg" src={form.primary_logo_url} /> : null}
          {form.secondary_logo_url ? <img alt="Logo secundario" className="h-14 max-w-[180px] rounded-md bg-white object-contain p-2 shadow-lg" src={form.secondary_logo_url} /> : null}
        </div>
        <div>
          <span className="inline-flex rounded-md bg-white/95 px-3 py-1 text-sm font-bold text-slate-900 shadow-sm">{form.title}</span>
          {form.event_name ? <h1 className="mt-4 max-w-3xl text-3xl font-bold md:text-5xl">{form.event_name}</h1> : null}
          {form.session_name || form.venue_name ? <p className="mt-2 text-base font-medium text-white/90">{[form.session_name, form.venue_name].filter(Boolean).join(" · ")}</p> : null}
        </div>
      </div>
    </header>
  );
}
