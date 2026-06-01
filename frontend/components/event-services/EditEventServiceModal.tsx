"use client";

import { ModalShell } from "@/components/common/ModalShell";
import { EventServiceForm } from "@/components/event-services/EventServiceForm";
import type { EventService, EventServiceUpdate } from "@/types/eventService";
import type { Service } from "@/types/service";

export function EditEventServiceModal({ item, services, loading, onClose, onSubmit }: { item: EventService; services: Service[]; loading?: boolean; onClose: () => void; onSubmit: (data: EventServiceUpdate) => Promise<void> }) {
  return (
    <ModalShell title="Editar servicio contratado" description={item.service?.name || "Servicio del evento"} onClose={onClose}>
      <EventServiceForm initialData={item} loading={loading} services={services} onCancel={onClose} onSubmit={(data) => onSubmit(data as EventServiceUpdate)} />
    </ModalShell>
  );
}
