"use client";

import { useCallback, useEffect, useState } from "react";

import { ClientAccessNotice } from "@/components/client/ClientAccessNotice";
import { ClientEventHeader } from "@/components/client/ClientEventHeader";
import { ClientEventTabs } from "@/components/client/ClientEventTabs";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { RoleGuard } from "@/components/layout/RoleGuard";
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
        {!loading && event ? <><ClientEventHeader event={event} /><ClientAccessNotice /><ClientEventTabs eventId={event.id} /></> : null}
      </div>
    </RoleGuard>
  );
}
