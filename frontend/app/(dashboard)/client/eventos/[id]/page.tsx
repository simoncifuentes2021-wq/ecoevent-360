"use client";

import { useCallback, useEffect, useState } from "react";
import { MapPin } from "lucide-react";

import { ClientAccessNotice } from "@/components/client/ClientAccessNotice";
import { ClientEventHeader } from "@/components/client/ClientEventHeader";
import { ClientEventTabs } from "@/components/client/ClientEventTabs";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Card, CardContent } from "@/components/ui/card";
import { getEvent } from "@/lib/api/events";
import type { Event } from "@/types/event";

export default function ClientEventDetailPage({ params }: { params: { id: string } }) {
  const [event, setEvent] = useState<Event | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEvent(await getEvent(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No tienes acceso a este evento.");
    } finally {
      setLoading(false);
    }
  }, [params.id]);

  useEffect(() => { void load(); }, [load]);

  return (
    <RoleGuard roles={["CLIENT"]}>
      <div className="space-y-6">
        {loading ? <LoadingState label="Cargando evento..." /> : null}
        {!loading && error ? <ErrorState message={error} title="No se pudo cargar el evento" onRetry={load} /> : null}
        {!loading && event ? <><ClientEventHeader event={event} /><LogisticsCard event={event} /><ClientAccessNotice /><ClientEventTabs eventId={event.id} /></> : null}
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
