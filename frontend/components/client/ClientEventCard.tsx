"use client";

import Link from "next/link";
import { CalendarDays, Eye, MapPin, Users } from "lucide-react";

import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import type { Event } from "@/types/event";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value));
}

export function ClientEventCard({ event }: { event: Event }) {
  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-950">{event.name}</h2>
            <p className="mt-1 text-sm text-slate-600">{event.event_type || "Evento contratado"}</p>
          </div>
          <EventStatusBadge status={event.status} />
        </div>
        <div className="grid gap-2 text-sm text-slate-600">
          <span className="flex items-center gap-2"><CalendarDays className="h-4 w-4 text-emerald-700" />{formatDate(event.start_date)} - {formatDate(event.end_date)}</span>
          <span className="flex items-center gap-2"><MapPin className="h-4 w-4 text-emerald-700" />{[event.location_name, event.city, event.region].filter(Boolean).join(", ") || "Sin ubicacion"}</span>
          <span className="flex items-center gap-2"><Users className="h-4 w-4 text-emerald-700" />{event.real_attendees ?? event.estimated_attendees ?? 0} asistentes {event.real_attendees ? "reales" : "estimados"}</span>
        </div>
        <Link href={`/client/eventos/${event.id}`}>
          <Button className="w-full" type="button"><Eye className="h-4 w-4" />Ver evento</Button>
        </Link>
      </CardContent>
    </Card>
  );
}
