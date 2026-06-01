import Link from "next/link";
import { Camera, ClipboardList, Plus, Recycle, ShieldCheck, ShieldAlert } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function SupervisorQuickActions() {
  const actions = [
    { label: "Ver tareas", href: "/worker/mis-tareas", icon: ClipboardList },
    { label: "Eventos asignados", href: "/supervisor/eventos", icon: Plus },
    { label: "Reportar incidencia", href: "/supervisor/reportar-incidencia", icon: ShieldAlert },
    { label: "Subir evidencia", href: "/supervisor/subir-evidencia", icon: Camera },
    { label: "Registrar residuo", href: "/supervisor/registrar-residuo", icon: Recycle },
    { label: "Ver alertas", href: "/supervisor/alertas", icon: ShieldCheck }
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {actions.map((action) => {
        const Icon = action.icon;
        return (
          <Card key={action.label}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><Icon className="h-5 w-5" /></div>
              <Link className="text-sm font-semibold text-slate-800 hover:text-emerald-800" href={action.href}>{action.label}</Link>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
