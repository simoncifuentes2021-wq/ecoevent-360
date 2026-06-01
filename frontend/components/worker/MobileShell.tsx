import type { ReactNode } from "react";

export function MobileShell({ title, description, children }: { title: string; description?: string; children: ReactNode }) {
  return (
    <div className="mx-auto min-h-[calc(100vh-120px)] max-w-2xl space-y-5 pb-24">
      <div className="rounded-b-3xl bg-emerald-800 px-5 py-6 text-white shadow-lg md:rounded-3xl">
        <p className="text-xs font-bold uppercase tracking-wide text-emerald-100">Terreno</p>
        <h1 className="mt-1 text-2xl font-bold">{title}</h1>
        {description ? <p className="mt-2 text-sm text-emerald-50">{description}</p> : null}
      </div>
      <div className="space-y-4 px-1">{children}</div>
    </div>
  );
}
