"use client";

import { ModalShell } from "@/components/common/ModalShell";
import { EventServiceForm } from "@/components/event-services/EventServiceForm";
import type { EventServiceCreate } from "@/types/eventService";
import type { Service } from "@/types/service";

export function AddEventServiceModal({ services, loading, onClose, onSubmit }: { services: Service[]; loading?: boolean; onClose: () => void; onSubmit: (data: EventServiceCreate) => Promise<void> }) {
  return (
    <ModalShell title="Agregar servicio" description="Contrata un servicio del catalogo para este evento." onClose={onClose}>
      <EventServiceForm loading={loading} services={services} onCancel={onClose} onSubmit={(data) => onSubmit(data as EventServiceCreate)} />
    </ModalShell>
  );
}
