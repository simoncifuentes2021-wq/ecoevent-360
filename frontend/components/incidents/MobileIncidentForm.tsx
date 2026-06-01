"use client";

import { useEffect, useState } from "react";

import { IncidentFormModal } from "@/components/incidents/IncidentFormModal";
import { getEventStaff } from "@/lib/api/staff";
import { getEventZones } from "@/lib/api/zones";
import type { IncidentCreate } from "@/types/incident";
import type { EventStaff } from "@/types/staff";
import type { Zone } from "@/types/zone";

export function MobileIncidentForm({ eventId, loading, onCancel, onSubmit }: { eventId: string; loading?: boolean; onCancel: () => void; onSubmit: (data: IncidentCreate) => Promise<void> }) {
  const [zones, setZones] = useState<Zone[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);

  useEffect(() => {
    void Promise.all([getEventZones(eventId), getEventStaff(eventId)]).then(([zoneData, staffData]) => {
      setZones(zoneData);
      setStaff(staffData);
    }).catch(() => {
      setZones([]);
      setStaff([]);
    });
  }, [eventId]);

  return <IncidentFormModal loading={loading} staff={staff} zones={zones} onClose={onCancel} onSubmit={(data) => onSubmit(data as IncidentCreate)} />;
}
