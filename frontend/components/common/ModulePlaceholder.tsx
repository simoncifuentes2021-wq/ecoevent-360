import type { LucideIcon } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { Card, CardContent } from "@/components/ui/card";

export function ModulePlaceholder({
  eyebrow,
  title,
  description,
  icon: Icon
}: {
  eyebrow: string;
  title: string;
  description: string;
  icon: LucideIcon;
}) {
  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-semibold uppercase text-primary">{eyebrow}</p>
        <h1 className="mt-1 text-3xl font-bold">{title}</h1>
        <p className="mt-2 max-w-2xl text-muted-foreground">{description}</p>
      </div>
      <Card>
        <CardContent className="flex items-center gap-4">
          <span className="grid h-12 w-12 place-items-center rounded-lg bg-emerald-50 text-primary">
            <Icon className="h-6 w-6" />
          </span>
          <div>
            <p className="font-semibold">Módulo preparado</p>
            <p className="text-sm text-muted-foreground">La estructura visual está lista para conectar el CRUD completo.</p>
          </div>
        </CardContent>
      </Card>
      <EmptyState title="Sin registros para mostrar" description="Cuando el módulo esté conectado, los registros aparecerán en esta vista." />
    </div>
  );
}
