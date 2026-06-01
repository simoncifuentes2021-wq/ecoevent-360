import Link from "next/link";
import { FileText, Plus, Sparkles, UserPlus } from "lucide-react";

import { Card, CardContent, CardHeader } from "@/components/ui/card";

const actions = [
  { href: "/clients", label: "Crear cliente", icon: Plus },
  { href: "/events", label: "Crear evento", icon: Sparkles },
  { href: "/users", label: "Crear usuario", icon: UserPlus },
  { href: "/reports", label: "Ver reportes", icon: FileText }
];

export function QuickActions() {
  return (
    <Card>
      <CardHeader>
        <h2 className="font-semibold">Acciones rápidas</h2>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <Link
              className="flex items-center gap-3 rounded-md border bg-white p-3 text-sm font-semibold transition hover:border-primary/40 hover:bg-emerald-50"
              href={action.href}
              key={action.href}
            >
              <span className="grid h-9 w-9 place-items-center rounded-md bg-primary text-primary-foreground">
                <Icon className="h-4 w-4" />
              </span>
              {action.label}
            </Link>
          );
        })}
      </CardContent>
    </Card>
  );
}
