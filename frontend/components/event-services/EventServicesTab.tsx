"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ErrorState } from "@/components/common/ErrorState";
import { AddEventServiceModal } from "@/components/event-services/AddEventServiceModal";
import { EditEventServiceModal } from "@/components/event-services/EditEventServiceModal";
import { EventServicesTable } from "@/components/event-services/EventServicesTable";
import { Button } from "@/components/ui/button";
import { createEventService, deleteEventService, getEventServices, updateEventService } from "@/lib/api/eventServices";
import { getServices } from "@/lib/api/services";
import { canManageEventServices } from "@/lib/permissions";
import type { EventService, EventServiceCreate, EventServiceUpdate } from "@/types/eventService";
import type { UserRole } from "@/types/roles";
import type { Service } from "@/types/service";

export function EventServicesTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [items, setItems] = useState<EventService[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<EventService | null>(null);
  const [deleting, setDeleting] = useState<EventService | null>(null);
  const canManage = canManageEventServices(role);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [eventServices, catalog] = await Promise.all([getEventServices(eventId), getServices({ page: 1, limit: 100 })]);
      const catalogById = new Map(catalog.items.map((service) => [service.id, service]));
      setItems((Array.isArray(eventServices) ? eventServices : []).map((item) => ({
        ...item,
        service: item.service ?? catalogById.get(item.service_id) ?? null
      })));
      setServices(catalog.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  async function saveCreate(data: EventServiceCreate) {
    setSaving(true);
    try {
      await createEventService(eventId, data);
      setAddOpen(false);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function saveUpdate(data: EventServiceUpdate) {
    if (!editing) return;
    setSaving(true);
    try {
      await updateEventService(eventId, editing.id, data);
      setEditing(null);
      await load();
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!deleting) return;
    await deleteEventService(eventId, deleting.id);
    setDeleting(null);
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Servicios contratados</h2>
          <p className="text-sm text-slate-600">Controla cantidad, precio y alcance de los servicios del evento.</p>
        </div>
        {canManage ? <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" />Agregar servicio</Button> : null}
      </div>
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      <EventServicesTable canManage={canManage} error={null} items={items} loading={loading} onDelete={setDeleting} onEdit={setEditing} />
      {addOpen ? <AddEventServiceModal loading={saving} services={services} onClose={() => setAddOpen(false)} onSubmit={saveCreate} /> : null}
      {editing ? <EditEventServiceModal item={editing} loading={saving} services={services} onClose={() => setEditing(null)} onSubmit={saveUpdate} /> : null}
      <ConfirmDialog open={Boolean(deleting)} title="Quitar servicio" description="El servicio se quitara de este evento." onClose={() => setDeleting(null)} onConfirm={confirmDelete} />
    </div>
  );
}
