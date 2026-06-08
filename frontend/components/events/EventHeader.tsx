import { CalendarDays, MapPin, Users } from "lucide-react";
import type { ReactNode } from "react";

import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Event } from "@/types/event";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function EventHeader({ event }: { event: Event }) {
  return (
    <Card className="overflow-hidden border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50">
      <CardContent className="space-y-5 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <EventStatusBadge status={event.status} />
              {event.hidden_from_operations ? <Badge tone="warning">Oculto al equipo operativo</Badge> : null}
              <span className="text-sm font-medium text-slate-500">{event.client?.business_name || "Cliente no informado"}</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">{event.name}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{event.description || "Evento preparado para gestion operativa, ambiental y sanitaria."}</p>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Info icon={<CalendarDays className="h-5 w-5" />} label="Fechas" value={`${formatDate(event.start_date)} - ${formatDate(event.end_date)}`} />
          <Info icon={<MapPin className="h-5 w-5" />} label="Ubicacion" value={[event.location_name, event.city, event.region].filter(Boolean).join(", ") || "Sin ubicacion"} />
          <Info icon={<Users className="h-5 w-5" />} label="Asistentes" value={`${event.estimated_attendees?.toLocaleString("es-CL") || 0} estimados`} />
        </div>
      </CardContent>
    </Card>
  );
}

function Info({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white/80 p-4">
      <div className="flex items-center gap-2 text-emerald-700">
        {icon}
        <span className="text-xs font-bold uppercase tracking-wide">{label}</span>
      </div>
      <p className="mt-2 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}
