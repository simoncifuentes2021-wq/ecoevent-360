import Link from "next/link";

export function LegalFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-6 text-sm text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <span>© {new Date().getFullYear()} Greenway App</span>
        <nav aria-label="Información legal" className="flex flex-wrap gap-x-5 gap-y-2">
          <Link className="hover:text-primary hover:underline" href="/privacidad">Política de privacidad</Link>
          <Link className="hover:text-primary hover:underline" href="/condiciones">Condiciones de uso</Link>
          <a className="hover:text-primary hover:underline" href="mailto:gonzalo@greenway.cl">Contacto</a>
        </nav>
      </div>
    </footer>
  );
}
