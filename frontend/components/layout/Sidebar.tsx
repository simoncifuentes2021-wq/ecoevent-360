"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, ChevronRight, Leaf } from "lucide-react";

import { cn } from "@/lib/utils";
import { roleNavigation } from "@/lib/routes";
import type { AuthUser } from "@/types/auth";

export function Sidebar({ user, onNavigate, collapsed = false, onToggleCollapse }: { user: AuthUser; onNavigate?: () => void; collapsed?: boolean; onToggleCollapse?: () => void }) {
  const pathname = usePathname();
  const items = roleNavigation[user.role];

  return (
    <aside className={cn("flex h-full min-h-0 w-full flex-col overflow-hidden border-r border-slate-200/80 bg-white py-4 shadow-soft transition-[width,padding] duration-200 md:sticky md:top-0 md:h-screen md:min-h-screen", collapsed ? "px-1.5 md:w-20" : "px-3 md:w-72")}>
      <div className={cn("mb-5 flex shrink-0 items-center", collapsed ? "flex-col justify-center gap-2" : "justify-between gap-2 px-2")}>
        <Link className={cn("flex min-w-0 items-center gap-3", collapsed && "justify-center")} href="/" onClick={onNavigate} aria-label="Greenway App" title={collapsed ? "Greenway App" : undefined}>
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-primary text-primary-foreground shadow-sm shadow-emerald-900/10">
            <Leaf className="h-5 w-5" />
          </span>
          {!collapsed ? <span className="min-w-0">
            <span className="block text-lg font-bold">Greenway App</span>
            <span className="block text-xs text-muted-foreground">Operacion sostenible</span>
          </span> : null}
        </Link>
        {onToggleCollapse ? <button type="button" aria-label={collapsed ? "Expandir menú lateral" : "Contraer menú lateral"} title={collapsed ? "Expandir menú" : "Contraer menú"} onClick={onToggleCollapse} className="grid h-8 w-8 shrink-0 place-items-center rounded-full text-slate-500 transition hover:bg-emerald-50 hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 focus-visible:ring-offset-2">
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button> : null}
      </div>
      <nav
        aria-label="Navegación principal"
        className={cn("sidebar-scrollbar-hidden grid min-h-0 flex-1 touch-pan-y auto-rows-max gap-1.5 overflow-y-auto overscroll-contain pb-4 [-webkit-overflow-scrolling:touch]", collapsed ? "px-0" : "pr-1")}
      >
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          if (item.disabled) {
            return (
              <button
                className={cn(
                  "flex h-11 cursor-not-allowed items-center gap-3 rounded-xl px-3 text-left text-sm font-semibold text-slate-400",
                  collapsed && "justify-center px-0",
                  item.indent && !collapsed && "ml-4 h-10 border-l border-slate-200 pl-4 text-xs"
                )}
                disabled
                key={item.href}
                title={collapsed ? `${item.label} · Próximamente` : "Proximamente"}
                type="button"
              >
                <Icon className="h-4 w-4" />
                {!collapsed ? <><span className="flex-1">{item.label}</span><span className="text-[10px] font-bold uppercase">Pronto</span></> : null}
              </button>
            );
          }
          return (
            <Link
              className={cn(
                "flex h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold text-slate-600 transition-colors hover:bg-emerald-50 hover:text-primary",
                collapsed && "justify-center px-0",
                item.indent && !collapsed && "ml-4 h-10 border-l border-slate-200 pl-4 text-xs",
                active && "bg-emerald-50 text-primary ring-1 ring-inset ring-emerald-100 hover:bg-emerald-50 hover:text-primary",
                collapsed && active && "shadow-sm"
              )}
              href={item.href}
              key={item.href}
              title={collapsed ? item.label : undefined}
              aria-label={collapsed ? item.label : undefined}
              aria-current={active ? "page" : undefined}
              onClick={onNavigate}
            >
              <Icon className="h-4 w-4" />
              {!collapsed ? item.label : null}
            </Link>
          );
        })}
      </nav>
      {!collapsed ? <div className="mt-2 shrink-0 rounded-lg border bg-slate-50 p-3 text-xs text-slate-600">
        <p className="font-semibold text-slate-900">Vista segun rol</p>
        <p className="mt-1">Solo veras acciones disponibles para tu perfil.</p>
      </div> : null}
    </aside>
  );
}
