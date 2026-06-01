"use client";

import { useEffect, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { EventServicesTable } from "@/components/event-services/EventServicesTable";
import { getEventServices } from "@/lib/api/eventServices";
import { getServices } from "@/lib/api/services";
import type { EventService } from "@/types/eventService";

export function ClientServicesTab({ eventId }: { eventId: string }) {
  const [items, setItems] = useState<EventService[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [eventServices, catalog] = await Promise.all([getEventServices(eventId), getServices({ page: 1, limit: 100 })]);
        const catalogById = new Map(catalog.items.map((service) => [service.id, service]));
        setItems(eventServices.map((item) => ({
          ...item,
          service: item.service ?? catalogById.get(item.service_id) ?? null
        })));
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudieron cargar los servicios.");
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [eventId]);

  return <EventServicesTable canManage={false} error={error} items={items} loading={loading} onDelete={() => {}} onEdit={() => {}} />;
}
