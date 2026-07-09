"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createEventSession, getEventSessions } from "@/lib/api/eventSessions";
import type { EventSession } from "@/types/eventSession";
import type { UserRole } from "@/types/roles";

export function EventSessionsTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [items, setItems] = useState<EventSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", session_date: "", start_time: "", end_time: "", venue_name: "", stage_name: "" });
  const canManage = role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setItems(await getEventSessions(eventId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar las sesiones.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  async function submit() {
    await createEventSession(eventId, {
      name: form.name.trim(),
      session_date: form.session_date || null,
      start_time: form.start_time || null,
      end_time: form.end_time || null,
      venue_name: form.venue_name.trim() || null,
      stage_name: form.stage_name.trim() || null,
      expected_attendees: 0,
      status: "PLANNED"
    });
    setOpen(false);
    setForm({ name: "", session_date: "", start_time: "", end_time: "", venue_name: "", stage_name: "" });
    await load();
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Programación</h2>
          <p className="text-sm text-slate-600">Shows, jornadas o funciones asociadas al evento.</p>
        </div>
        {canManage ? <Button onClick={() => setOpen(true)} type="button"><Plus className="h-4 w-4" />Crear show</Button> : null}
      </div>
      {loading ? <LoadingState label="Cargando programación..." /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error ? (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {items.map((item) => (
            <article className="rounded-lg border bg-white p-4 shadow-sm" key={item.id}>
              <h3 className="font-bold text-slate-950">{item.name}</h3>
              <p className="mt-1 text-sm text-slate-600">{[item.session_date, item.start_time, item.venue_name].filter(Boolean).join(" · ") || "Sin fecha definida"}</p>
              {item.stage_name ? <p className="mt-2 text-xs font-semibold text-emerald-700">{item.stage_name}</p> : null}
            </article>
          ))}
          {!items.length ? <p className="text-sm text-slate-500">Aún no hay shows creados.</p> : null}
        </div>
      ) : null}
      {open ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
          <div className="w-full max-w-xl rounded-lg bg-white p-5 shadow-2xl">
            <h3 className="text-lg font-bold">Crear show o sesión</h3>
            <div className="mt-4 grid gap-3">
              <Input placeholder="Nombre" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              <div className="grid gap-3 md:grid-cols-3">
                <Input type="date" value={form.session_date} onChange={(event) => setForm({ ...form, session_date: event.target.value })} />
                <Input type="time" value={form.start_time} onChange={(event) => setForm({ ...form, start_time: event.target.value })} />
                <Input type="time" value={form.end_time} onChange={(event) => setForm({ ...form, end_time: event.target.value })} />
              </div>
              <Input placeholder="Venue / recinto" value={form.venue_name} onChange={(event) => setForm({ ...form, venue_name: event.target.value })} />
              <Input placeholder="Escenario" value={form.stage_name} onChange={(event) => setForm({ ...form, stage_name: event.target.value })} />
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button disabled={!form.name} type="button" onClick={submit}>Crear</Button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
