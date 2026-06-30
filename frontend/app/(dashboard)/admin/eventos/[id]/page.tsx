"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CalendarClock, Edit, EyeOff, MapPin, Users } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { EventHeader } from "@/components/events/EventHeader";
import { EventTabs } from "@/components/events/EventTabs";
import { StatusChangeDialog } from "@/components/events/StatusChangeDialog";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAuth } from "@/hooks/useAuth";
import { changeEventOperationalVisibility, changeEventStatus, getEvent } from "@/lib/api/events";
import type { Event, EventStatus } from "@/types/event";

export default function EventDetailPage({ params }: { params: { id: string } }) {
  const { user } = useAuth();
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusOpen, setStatusOpen] = useState(false);
  const [visibilityOpen, setVisibilityOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvent(await getEvent(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No pudimos cargar el evento.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function updateStatus(status: EventStatus) {
    setStatusLoading(true);
    try {
      await changeEventStatus(params.id, status);
      setStatusOpen(false);
      await load();
    } finally {
      setStatusLoading(false);
    }
  }

  async function toggleOperationalVisibility() {
    if (!event) return;
    try {
      await changeEventOperationalVisibility(event.id, !event.hidden_from_operations);
      setVisibilityOpen(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar la visibilidad operativa.");
      setVisibilityOpen(false);
    }
  }

  if (loading) return <LoadingState label="Cargando evento..." />;
  if (error || !event) return <ErrorState message={error || "Evento no encontrado"} title="No pudimos cargar el evento" onRetry={load} />;

  return (
    <RoleGuard roles={["SUPER_ADMIN", "ADMIN"]}>
      <div className="space-y-6">
        <PageHeader
          title="Detalle de evento"
          description="Centro operativo preparado para servicios, zonas, personal y tareas."
          actions={
            <div className="flex flex-wrap gap-2">
              <Link href="/admin/eventos">
                <Button variant="secondary">
                  <ArrowLeft className="h-4 w-4" />
                  Volver
                </Button>
              </Link>
              <Button variant="secondary" onClick={() => setStatusOpen(true)}>
                <CalendarClock className="h-4 w-4" />
                Estado
              </Button>
              <Button variant="secondary" onClick={() => setVisibilityOpen(true)}>
                {event.hidden_from_operations ? <Users className="h-4 w-4" /> : <EyeOff className="h-4 w-4" />}
                {event.hidden_from_operations ? "Mostrar equipo" : "Ocultar equipo"}
              </Button>
              <Link href={`/admin/eventos/${event.id}/editar`}>
                <Button>
                  <Edit className="h-4 w-4" />
                  Editar
                </Button>
              </Link>
            </div>
          }
        />
        <EventHeader event={event} />
        <LogisticsCard event={event} />
        <EventTabs event={event} eventId={event.id} role={user?.role} />
        <ConfirmDialog
          description={
            event.hidden_from_operations
              ? "Supervisores y trabajadores volveran a ver este evento si tienen asignaciones o tareas."
              : "Supervisores y trabajadores dejaran de ver este evento, incluyendo tareas asignadas y accesos operativos."
          }
          open={visibilityOpen}
          title={event.hidden_from_operations ? "Mostrar al equipo operativo" : "Ocultar al equipo operativo"}
          onClose={() => setVisibilityOpen(false)}
          onConfirm={toggleOperationalVisibility}
        />
        <StatusChangeDialog event={statusOpen ? event : null} loading={statusLoading} role={user?.role} onClose={() => setStatusOpen(false)} onConfirm={updateStatus} />
      </div>
    </RoleGuard>
  );
}

function LogisticsCard({ event }: { event: Event }) {
  const location = [event.location_name, event.city, event.region, event.country].filter(Boolean).join(", ");
  const latitude = event.latitude === null || event.latitude === undefined || event.latitude === "" ? "No informada" : String(event.latitude);
  const longitude = event.longitude === null || event.longitude === undefined || event.longitude === "" ? "No informada" : String(event.longitude);

  return (
    <Card>
      <CardContent className="space-y-4 p-5">
        <div className="flex items-center gap-2 text-slate-900">
          <MapPin className="h-5 w-5 text-emerald-700" />
          <h2 className="text-lg font-bold">Datos logísticos</h2>
        </div>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-4">
          <LogisticsInfo label="Ubicación" value={location || "Sin ubicación registrada"} />
          <LogisticsInfo label="Dirección" value={event.address || "Sin dirección registrada"} />
          <LogisticsInfo label="Latitud" value={latitude} />
          <LogisticsInfo label="Longitud" value={longitude} />
        </div>
      </CardContent>
    </Card>
  );
}

function LogisticsInfo({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-semibold text-slate-800">{value}</p>
    </div>
  );
}
