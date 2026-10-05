import { CalendarDays, MapPin, Users } from "lucide-react";

import { EventStatusBadge } from "@/components/events/EventStatusBadge";
import { Card, CardContent } from "@/components/ui/card";
import { formatDashboardPercentage } from "@/lib/normalizers/dashboard";
import type { EventDashboard } from "@/types/dashboard";
import type { Event } from "@/types/event";

function formatDate(value?: string | null) {
  if (!value) return "Fecha no informada";

  const parsed = new Date(value);
  if (!Number.isNaN(parsed.getTime())) {
    return new Intl.DateTimeFormat("es-CL", { day: "2-digit", month: "short", year: "numeric" }).format(parsed);
  }

  const dayFirstDate = value.match(/^(\d{2})-(\d{2})-(\d{4})/);
  if (dayFirstDate) {
    const [, day, month, year] = dayFirstDate;
    const fallback = new Date(Number(year), Number(month) - 1, Number(day));
    if (!Number.isNaN(fallback.getTime())) {
      return new Intl.DateTimeFormat("es-CL", { day: "2-digit", month: "short", year: "numeric" }).format(fallback);
    }
  }

  return "Fecha no informada";
}

function formatDateRange(start?: string | null, end?: string | null) {
  return `${formatDate(start)} — ${formatDate(end)}`;
}

function eventLocation(event: Event) {
  return [event.location_name, event.city, event.region].filter(Boolean).join(", ") || "Ubicación no informada";
}

export function EventExecutiveHeader({ dashboard, event }: { dashboard: EventDashboard; event?: Event }) {
  const eventData = event ?? dashboard.event;
  if (!eventData) return null;

  const hasTasks = dashboard.tasks.total > 0;
  const completionRate = Math.min(100, Math.max(0, dashboard.tasks.completion_rate));
  const attendees = eventData.real_attendees || eventData.estimated_attendees;

  return (
    <Card className="overflow-hidden border-slate-200/80 shadow-[0_12px_32px_-24px_rgba(15,23,42,0.45)]">
      <div className="border-b border-slate-200/80 bg-gradient-to-r from-slate-950 via-slate-900 to-emerald-950 px-6 py-6 text-white sm:px-8">
        <div className="flex flex-col justify-between gap-5 lg:flex-row lg:items-start">
          <div className="min-w-0">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">Resumen ejecutivo</p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h2 className="max-w-4xl text-2xl font-bold tracking-tight sm:text-3xl">{eventData.name}</h2>
              <EventStatusBadge status={eventData.status} />
            </div>
            <p className="mt-2 max-w-3xl text-sm text-slate-300">Vista consolidada del desempeño operativo, ambiental y de experiencia del evento.</p>
          </div>
          {hasTasks ? (
            <div className="w-full shrink-0 rounded-xl border border-white/10 bg-white/10 p-4 backdrop-blur lg:max-w-[220px]">
              <div className="flex items-center justify-between gap-3 text-xs font-semibold text-slate-300">
                <span>Avance operativo</span>
                <span className="text-white">{formatDashboardPercentage(completionRate)}</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/15">
                <div className="h-full rounded-full bg-emerald-400 transition-all" style={{ width: `${completionRate}%` }} />
              </div>
              <p className="mt-2 text-xs text-slate-300">{dashboard.tasks.completed} de {dashboard.tasks.total} tareas completadas</p>
            </div>
          ) : null}
        </div>
      </div>
      <CardContent className="grid gap-4 bg-white px-6 py-5 sm:grid-cols-3 sm:px-8">
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-50 text-emerald-700"><CalendarDays className="h-4 w-4" /></span>
          <div><p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Fechas</p><p className="mt-1 text-sm font-semibold text-slate-800">{formatDateRange(eventData.start_date, eventData.end_date)}</p></div>
        </div>
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-sky-50 text-sky-700"><MapPin className="h-4 w-4" /></span>
          <div><p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Ubicación</p><p className="mt-1 text-sm font-semibold text-slate-800">{eventLocation(eventData)}</p></div>
        </div>
        <div className="flex items-start gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-violet-50 text-violet-700"><Users className="h-4 w-4" /></span>
          <div><p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">Asistentes</p><p className="mt-1 text-sm font-semibold text-slate-800">{attendees ? `${new Intl.NumberFormat("es-CL").format(attendees)} estimados` : "Sin estimación"}</p></div>
        </div>
      </CardContent>
    </Card>
  );
}
