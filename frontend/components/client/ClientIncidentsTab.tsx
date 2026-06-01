"use client";

import { useEffect, useState } from "react";

import { IncidentTable } from "@/components/incidents/IncidentTable";
import { getEventIncidents } from "@/lib/api/incidents";
import type { Incident } from "@/types/incident";

export function ClientIncidentsTab({ eventId }: { eventId: string }) {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getEventIncidents(eventId);
        setIncidents(data.items);
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar las incidencias.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  return <IncidentTable canClose={false} canEdit={false} canResolve={false} error={error} incidents={incidents} loading={loading} onCloseIncident={() => {}} onEdit={() => {}} onResolve={() => {}} onView={() => {}} />;
}
