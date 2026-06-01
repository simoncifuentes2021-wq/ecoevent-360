"use client";

import Link from "next/link";
import { ArrowLeft, CalendarDays, MapPin, Users } from "lucide-react";

import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Event } from "@/types/event";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function ClientEventHeader({ event }: { event: Event }) {
  return (
    <Card className="overflow-hidden border-emerald-100 bg-gradient-to-br from-white via-white to-emerald-50">
      <CardContent className="space-y-5 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <EventStatusBadge status={event.status} />
              <span className="text-sm font-medium text-slate-500">{event.client?.business_name || "Tu evento"}</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-950">{event.name}</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{event.description || "Resumen ejecutivo del servicio contratado."}</p>
          </div>
          <Link href="/client/mis-eventos">
            <Button type="button" variant="secondary"><ArrowLeft className="h-4 w-4" />Volver</Button>
          </Link>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Info icon={<CalendarDays className="h-5 w-5" />} label="Fechas" value={`${formatDate(event.start_date)} - ${formatDate(event.end_date)}`} />
          <Info icon={<MapPin className="h-5 w-5" />} label="Ubicacion" value={[event.location_name, event.city, event.region].filter(Boolean).join(", ") || "Sin ubicacion"} />
          <Info icon={<Users className="h-5 w-5" />} label="Asistentes" value={`${(event.real_attendees ?? event.estimated_attendees ?? 0).toLocaleString("es-CL")} ${event.real_attendees ? "reales" : "estimados"}`} />
        </div>
      </CardContent>
    </Card>
  );
}

function Info({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="rounded-2xl border border-slate-200 bg-white/80 p-4"><div className="flex items-center gap-2 text-emerald-700">{icon}<span className="text-xs font-bold uppercase tracking-wide">{label}</span></div><p className="mt-2 text-sm font-semibold text-slate-800">{value}</p></div>;
}
