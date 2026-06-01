"use client";

import Link from "next/link";
import { CalendarDays, ClipboardList, MapPin } from "lucide-react";

import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Button } from "@/components/ui/button";
import type { Event } from "@/types/event";

function date(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium" }).format(new Date(value));
}

export function SupervisorEventCard({ event, pendingTasks = 0 }: { event: Event; pendingTasks?: number }) {
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-950">{event.name}</h2>
          <p className="mt-1 text-sm text-slate-600">{event.client?.business_name || "Cliente"}</p>
        </div>
        <EventStatusBadge status={event.status} />
      </div>
      <div className="mt-4 grid gap-2 text-sm text-slate-600">
        <span className="flex items-center gap-2"><CalendarDays className="h-4 w-4 text-emerald-700" />{date(event.start_date)}</span>
        <span className="flex items-center gap-2"><MapPin className="h-4 w-4 text-emerald-700" />{[event.city, event.region].filter(Boolean).join(", ") || "Sin ubicacion"}</span>
        <span className="flex items-center gap-2"><ClipboardList className="h-4 w-4 text-emerald-700" />{pendingTasks} tareas pendientes</span>
      </div>
      <Link className="mt-5 block" href={`/supervisor/eventos/${event.id}`}>
        <Button className="w-full">Gestionar evento</Button>
      </Link>
    </div>
  );
}
