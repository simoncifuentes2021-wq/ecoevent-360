"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Camera } from "lucide-react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { RoleGuard } from "@/components/layout/RoleGuard";
import { Button } from "@/components/ui/button";
import { MobileShell } from "@/components/worker/MobileShell";
import { MobileWasteForm } from "@/components/waste/MobileWasteForm";
import { ApiError } from "@/lib/api";
import { getEventEvidences } from "@/lib/api/evidences";
import { getEvents } from "@/lib/api/events";
import { createWasteRecord } from "@/lib/api/waste";
import { getWasteTypes } from "@/lib/api/wasteTypes";
import { getEventZones } from "@/lib/api/zones";
import type { Event } from "@/types/event";
import type { Evidence } from "@/types/evidence";
import type { WasteRecordCreate, WasteType } from "@/types/waste";
import type { Zone } from "@/types/zone";

export default function WorkerWastePage() {
  const router = useRouter();
  const params = useSearchParams();
  const { toast } = useToast();
  const [events, setEvents] = useState<Event[]>([]);
  const [eventId, setEventId] = useState(params.get("event_id") || "");
  const [zones, setZones] = useState<Zone[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [wasteTypes, setWasteTypes] = useState<WasteType[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const eventData = await getEvents({ page: 1, limit: 100 });
      const selected = eventId || eventData.items[0]?.id || "";
      setEvents(eventData.items);
      setEventId(selected);
      const [zoneData, evidenceData, typeData] = selected
        ? await Promise.all([getEventZones(selected), getEventEvidences(selected), getWasteTypes().catch(() => [])])
        : [[], { items: [] }, []];
      setZones(zoneData);
      setEvidences(evidenceData.items);
      setWasteTypes(typeData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la informacion.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  async function submit(data: WasteRecordCreate) {
    if (!eventId) return;
    setSaving(true);
    try {
      await createWasteRecord(eventId, data);
      toast({ tone: "success", title: "Residuo registrado" });
      router.push("/worker/mis-tareas");
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "No se pudo registrar el residuo.";
      toast({ tone: "error", title: "Error al registrar", description: message });
    } finally {
      setSaving(false);
    }
  }

  return (
    <RoleGuard roles={["WORKER", "SUPERVISOR"]}>
      <MobileShell title="Registrar residuo" description="Ingresa tipo, peso, destino y evidencia ambiental.">
        {loading ? <LoadingState label="Cargando datos..." /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {!loading && events.length === 0 ? <EmptyState title="Sin eventos" description="No tienes eventos disponibles para registrar residuos." /> : null}
        {events.length > 0 ? (
          <div className="space-y-4">
            <label className="grid gap-2 text-sm font-semibold">Evento<select className="h-12 rounded-2xl border px-4" value={eventId} onChange={(event) => setEventId(event.target.value)}>{events.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
            <Link href={`/worker/subir-evidencia?event_id=${eventId}`}><Button className="w-full" variant="secondary"><Camera className="h-4 w-4" />Subir evidencia primero</Button></Link>
            <MobileWasteForm evidences={evidences} loading={saving} wasteTypes={wasteTypes} zones={zones} onCancel={() => router.push("/worker/mis-tareas")} onSubmit={submit} />
          </div>
        ) : null}
      </MobileShell>
    </RoleGuard>
  );
}
