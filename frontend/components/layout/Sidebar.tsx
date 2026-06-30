"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Leaf } from "lucide-react";

import { cn } from "@/lib/utils";
import { roleNavigation } from "@/lib/routes";
import type { AuthUser } from "@/types/auth";

export function Sidebar({ user, onNavigate }: { user: AuthUser; onNavigate?: () => void }) {
  const pathname = usePathname();
  const items = roleNavigation[user.role];

  return (
    <aside className="flex h-full min-h-screen w-72 flex-col border-r bg-white/95 px-3 py-4 shadow-soft">
      <Link className="mb-6 flex items-center gap-3 px-3" href="/">
        <span className="grid h-11 w-11 place-items-center rounded-lg bg-primary text-primary-foreground">
          <Leaf className="h-5 w-5" />
        </span>
        <span>
          <span className="block text-lg font-bold">EcoEvent 360</span>
          <span className="block text-xs text-muted-foreground">Operacion sostenible</span>
        </span>
      </Link>
      <nav className="grid gap-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          if (item.disabled) {
            return (
              <button
                className={cn(
                  "flex h-11 cursor-not-allowed items-center gap-3 rounded-md px-3 text-left text-sm font-semibold text-slate-400",
                  item.indent && "ml-4 h-10 border-l border-slate-200 pl-4 text-xs"
                )}
                disabled
                key={item.href}
                title="Proximamente"
                type="button"
              >
                <Icon className="h-4 w-4" />
                <span className="flex-1">{item.label}</span>
                <span className="text-[10px] font-bold uppercase">Pronto</span>
              </button>
            );
          }
          return (
            <Link
              className={cn(
                "flex h-11 items-center gap-3 rounded-md px-3 text-sm font-semibold text-slate-600 transition hover:bg-emerald-50 hover:text-primary",
                item.indent && "ml-4 h-10 border-l border-slate-200 pl-4 text-xs",
                active && "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground"
              )}
              href={item.href}
              key={item.href}
              onClick={onNavigate}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="mt-auto rounded-lg border bg-slate-50 p-3 text-xs text-slate-600">
        <p className="font-semibold text-slate-900">Vista segun rol</p>
        <p className="mt-1">Solo veras acciones disponibles para tu perfil.</p>
      </div>
    </aside>
  );
}
