"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarClock, MapPin } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { getEvent } from "@/lib/api/events";
import { getEventZones } from "@/lib/api/zones";
import type { Event } from "@/types/event";
import type { Zone } from "@/types/zone";

function shortDate(value?: string | null) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "full" }).format(new Date(value));
}

export default function WorkerEventDetailPage({ params }: { params: { id: string } }) {
  const [event, setEvent] = useState<Event | null>(null);
  const [zones, setZones] = useState<Zone[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventData, zoneData] = await Promise.all([getEvent(params.id), getEventZones(params.id)]);
      setEvent(eventData);
      setZones(zoneData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el evento.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  const location = useMemo(() => {
    if (!event) return "";
    return [event.location_name, event.city, event.region].filter(Boolean).join(" â€¢ ");
  }, [event]);

  if (loading) return <LoadingState label="Cargando evento..." />;
  if (error || !event) return <ErrorState title="No pudimos cargar el evento" message={error || "Evento no encontrado"} onRetry={load} />;

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title={event.name} description={event.description || "Detalle del evento"}>
        <Link href="/worker/eventos">
          <Button className="w-full" variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Volver a eventos
          </Button>
        </Link>

        <div className="rounded-3xl border bg-white p-5 shadow-sm">
          <div className="grid gap-2 text-sm text-slate-700">
            <p className="flex items-center gap-2">
              <CalendarClock className="h-4 w-4 text-emerald-700" />
              {shortDate(event.start_date)} â€” {shortDate(event.end_date)}
            </p>
            {location ? (
              <p className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-emerald-700" />
                {location}
              </p>
            ) : null}
          </div>
        </div>

        <section className="space-y-3">
          <h2 className="text-base font-bold text-slate-950">Zonas</h2>
          {zones.length === 0 ? (
            <EmptyState title="Sin zonas registradas" description="AÃºn no hay zonas configuradas para este evento." />
          ) : (
            <div className="grid gap-2 sm:grid-cols-2">
              {zones.map((zone) => (
                <div className="rounded-3xl border bg-white p-4 text-sm font-semibold text-slate-900 shadow-sm" key={zone.id}>
                  {zone.name}
                </div>
              ))}
            </div>
          )}
        </section>
      </MobileShell>
    </RoleGuard>
  );
}

