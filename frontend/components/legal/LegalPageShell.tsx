import type { ReactNode } from "react";
import Link from "next/link";
import { Leaf } from "lucide-react";

export function LegalPageShell({
  title,
  description,
  updatedAt,
  children
}: {
  title: string;
  description: string;
  updatedAt: string;
  children: ReactNode;
}) {
  return (
    <main className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-5 py-4">
          <Link className="flex items-center gap-3 font-bold" href="/">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Leaf className="h-5 w-5" />
            </span>
            Greenway App
          </Link>
          <Link className="text-sm font-semibold text-primary hover:underline" href="/login">
            Ingresar a la plataforma
          </Link>
        </div>
      </header>
      <article className="mx-auto max-w-4xl px-5 py-12 sm:py-16">
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-primary">Greenway App · Información legal</p>
        <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-5xl">{title}</h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">{description}</p>
        <p className="mt-3 text-sm text-slate-500">Última actualización: {updatedAt}</p>
        <div className="mt-10 space-y-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-10 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:tracking-tight [&_p]:mt-3 [&_p]:leading-7 [&_ul]:mt-3 [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6 [&_li]:leading-7 [&_a]:font-semibold [&_a]:text-primary [&_a]:underline">
          {children}
        </div>
        <nav aria-label="Documentos legales" className="mt-8 flex flex-wrap gap-x-6 gap-y-3 text-sm">
          <Link className="font-semibold text-primary hover:underline" href="/privacidad">Política de privacidad</Link>
          <Link className="font-semibold text-primary hover:underline" href="/condiciones">Condiciones de uso</Link>
          <a className="font-semibold text-primary hover:underline" href="mailto:gonzalo@greenway.cl">Contacto Greenway</a>
        </nav>
      </article>
    </main>
  );
}
