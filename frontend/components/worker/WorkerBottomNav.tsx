"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AlertTriangle, Camera, ClipboardList, Flame, Home, LogOut, Recycle, ShieldAlert, UserRound } from "lucide-react";

import { cn } from "@/lib/utils";
import { useAuth } from "@/hooks/useAuth";

const items = [
  { href: "/worker/dashboard", label: "Inicio", icon: Home },
  { href: "/worker/mis-tareas", label: "Tareas", icon: ClipboardList },
  { href: "/worker/incidencias", label: "Incid.", icon: ShieldAlert },
  { href: "/worker/reportar-incidencia", label: "Reportar", icon: AlertTriangle },
  { href: "/worker/subir-evidencia", label: "Evid.", icon: Camera },
  { href: "/worker/registrar-residuo", label: "Residuos", icon: Recycle },
  { href: "/worker/registrar-consumo", label: "Consumo", icon: Flame },
  { href: "/worker/cuenta", label: "Cuenta", icon: UserRound }
] as const;

export function WorkerBottomNav() {
  const pathname = usePathname();
  const { logout } = useAuth();

  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t bg-white/95 backdrop-blur md:hidden">
      <nav className="mx-auto grid max-w-2xl grid-cols-9 gap-1 px-2 py-2">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              className={cn(
                "grid place-items-center gap-1 rounded-2xl px-1 py-2 text-[11px] font-semibold text-slate-600 hover:bg-emerald-50 hover:text-emerald-800",
                active && "bg-emerald-50 text-emerald-900"
              )}
              href={item.href}
              key={item.href}
            >
              <Icon className="h-5 w-5" />
              {item.label}
            </Link>
          );
        })}
        <button
          className="grid place-items-center gap-1 rounded-2xl px-1 py-2 text-[11px] font-semibold text-slate-600 hover:bg-rose-50 hover:text-rose-700"
          onClick={logout}
          type="button"
        >
          <LogOut className="h-5 w-5" />
          Salir
        </button>
      </nav>
    </div>
  );
}
