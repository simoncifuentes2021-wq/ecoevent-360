import { BriefcaseBusiness, ClipboardList, MapPin, Users } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function EventOperationalSummary() {
  const items = [
    { label: "Servicios", value: "Contratacion", icon: BriefcaseBusiness },
    { label: "Zonas", value: "Cobertura", icon: MapPin },
    { label: "Personal", value: "Equipo", icon: Users },
    { label: "Tareas", value: "Operacion", icon: ClipboardList }
  ];

  return (
    <div className="grid gap-3 md:grid-cols-4">
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <Card key={item.label}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700">
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-950">{item.label}</p>
                <p className="text-xs text-slate-500">{item.value}</p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
