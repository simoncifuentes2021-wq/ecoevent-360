"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, Check, LoaderCircle, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { createEventForm, getEventForms } from "@/lib/api/eventForms";
import { getClients } from "@/lib/api/clients";
import { getEvents } from "@/lib/api/events";
import { getEventSessions } from "@/lib/api/eventSessions";
import type { Event } from "@/types/event";
import type { EventForm, EventFormCreate, EventFormType } from "@/types/eventForm";
import type { EventSession } from "@/types/eventSession";

const bulkTypes: { type: EventFormType; label: string; title: string }[] = [
  { type: "TRANSPORT_SURVEY", label: "Transporte público", title: "Transporte público" },
  { type: "STAFF_TRANSPORT_SURVEY", label: "Transporte personal", title: "Transporte personal" },
  { type: "BIKE_ZONE_REGISTRATION", label: "Bike Zone", title: "Bike Zone" },
];

type Target = { event_id: string; event_name: string; session_id: string | null; session_name: string | null };
type Scope = "EVENT" | "SESSION";
type RunResult = { created: string[]; skipped: string[]; failed: string[] };

function targetKey(eventId: string, sessionId: string | null, type: EventFormType) {
  return `${eventId}:${sessionId || "EVENT"}:${type}`;
}

function eventDate(event: Event) {
  const format = (value: string) => new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", dateStyle: "medium" }).format(new Date(`${value.slice(0, 10)}T12:00:00Z`));
  return `${format(event.start_date)} – ${format(event.end_date)}`;
}

export function EventFormsBulkCreateDialog({ initialEventId, onClose, onComplete }: { initialEventId?: string; onClose: () => void; onComplete: () => void }) {
  const [events, setEvents] = useState<Event[]>([]);
  const [scope, setScope] = useState<Scope>("EVENT");
  const [selectedEventIds, setSelectedEventIds] = useState<string[]>(initialEventId ? [initialEventId] : []);
  const [sessions, setSessions] = useState<EventSession[]>([]);
  const [selectedSessionIds, setSelectedSessionIds] = useState<string[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<EventFormType[]>(bulkTypes.map(({ type }) => type));
  const [titles, setTitles] = useState<Record<EventFormType, string>>({
    TRANSPORT_SURVEY: "Transporte público",
    STAFF_TRANSPORT_SURVEY: "Transporte personal",
    BIKE_ZONE_REGISTRATION: "Bike Zone",
    EXPERIENCE_SURVEY: "Experiencia",
    CUSTOM: "Personalizado",
  });
  const [checking, setChecking] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [existingKeys, setExistingKeys] = useState<Set<string> | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let active = true;
    Promise.all([getEvents({ page: 1, limit: 100 }), getClients({ page: 1, limit: 100 })]).then(([eventResponse, clientResponse]) => {
      if (!active) return;
      const clientsById = new Map(clientResponse.items.map((client) => [client.id, client]));
      setEvents(eventResponse.items.map((event) => ({
        ...event,
        client: event.client || clientsById.get(event.client_id) || null,
      })));
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "No se pudieron cargar los eventos.");
    });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    if (scope !== "SESSION" || !selectedEventIds.length) {
      setSessions([]);
      setSelectedSessionIds([]);
      return;
    }
    setSessionsLoading(true);
    setError(null);
    Promise.all(selectedEventIds.map(async (eventId) => {
      const sessionsForEvent = await getEventSessions(eventId);
      const eventName = events.find((event) => event.id === eventId)?.name || "Evento";
      return sessionsForEvent.filter((session) => !session.archived_at).map((session) => ({ ...session, event_name: eventName }));
    })).then((groups) => {
      if (!active) return;
      const all = groups.flat();
      setSessions(all);
      setSelectedSessionIds((current) => current.filter((id) => all.some((session) => session.id === id)));
    }).catch((cause) => {
      if (active) setError(cause instanceof Error ? cause.message : "No se pudieron cargar las programaciones.");
    }).finally(() => { if (active) setSessionsLoading(false); });
    return () => { active = false; };
  }, [scope, selectedEventIds, events]);

  const targets = useMemo<Target[]>(() => {
    if (scope === "EVENT") return events.filter((event) => selectedEventIds.includes(event.id)).map((event) => ({ event_id: event.id, event_name: event.name, session_id: null, session_name: null }));
    return sessions.filter((session) => selectedSessionIds.includes(session.id)).map((session) => ({
      event_id: session.event_id,
      event_name: (session as EventSession & { event_name?: string }).event_name || events.find((event) => event.id === session.event_id)?.name || "Evento",
      session_id: session.id,
      session_name: session.name,
    }));
  }, [events, scope, selectedEventIds, selectedSessionIds, sessions]);

  const total = targets.length * selectedTypes.length;

  function toggleEvent(id: string) {
    setSelectedEventIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
    setExistingKeys(null);
    setResult(null);
  }

  function toggleSession(id: string) {
    setSelectedSessionIds((current) => current.includes(id) ? current.filter((value) => value !== id) : [...current, id]);
    setExistingKeys(null);
    setResult(null);
  }

  function toggleType(type: EventFormType) {
    setSelectedTypes((current) => current.includes(type) ? current.filter((value) => value !== type) : [...current, type]);
    setExistingKeys(null);
    setResult(null);
  }

  async function reviewBatch() {
    if (!total) return;
    setChecking(true);
    setError(null);
    try {
      const eventIds = Array.from(new Set(targets.map((target) => target.event_id)));
      const formsByEvent = await Promise.all(eventIds.map(async (id) => {
        const forms = await getEventForms(id, { page: 1, limit: 100, include_archived: true });
        return [id, forms.items] as const;
      }));
      const lookup = new Map<string, EventForm[]>(formsByEvent);
      const found = new Set<string>();
      for (const target of targets) {
        for (const type of selectedTypes) {
          const exists = (lookup.get(target.event_id) || []).some((form) => form.form_type === type && (form.session_id || null) === target.session_id);
          if (exists) found.add(targetKey(target.event_id, target.session_id, type));
        }
      }
      setExistingKeys(found);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "No se pudo revisar si ya existen formularios.");
    } finally { setChecking(false); }
  }

  async function createBatch() {
    if (!existingKeys || !total) return;
    setCreating(true);
    setError(null);
    setProgress(0);
    const created: string[] = [];
    const skipped: string[] = [];
    const failed: string[] = [];
    const jobs = targets.flatMap((target) => selectedTypes.map((type) => ({ target, type })));
    let nextJob = 0;
    const processJobs = async () => {
      while (nextJob < jobs.length) {
        const job = jobs[nextJob++];
        const { target, type } = job;
        const description = `${titles[type]} · ${target.event_name}${target.session_name ? ` · ${target.session_name}` : ""}`;
        if (existingKeys.has(targetKey(target.event_id, target.session_id, type))) {
          skipped.push(description);
        } else {
          const data: EventFormCreate = {
            title: titles[type].trim(),
            form_type: type,
            session_id: target.session_id,
            default_language: "es",
            requires_language_selection: true,
            available_languages: ["es", "en", "pt", "ko"],
            generate_template: true,
          };
          try {
            await createEventForm(target.event_id, data);
            created.push(description);
          } catch (cause) {
            failed.push(`${description}: ${cause instanceof Error ? cause.message : "error al crear"}`);
          }
        }
        setProgress((value) => value + 1);
      }
    };
    await Promise.all(Array.from({ length: Math.min(3, jobs.length) }, () => processJobs()));
    setResult({ created, skipped, failed });
    setCreating(false);
    if (created.length) onComplete();
  }

  const remaining = existingKeys ? total - existingKeys.size : total;

  return <div className="fixed inset-0 z-[90] grid place-items-center overflow-y-auto bg-slate-950/55 p-3 backdrop-blur-sm sm:p-6" role="dialog" aria-modal="true" aria-labelledby="bulk-form-title">
    <section className="my-auto max-h-[94vh] w-full max-w-3xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl sm:p-7">
      <header className="flex items-start justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Creación masiva</p><h2 id="bulk-form-title" className="mt-1 text-xl font-bold text-slate-950">Crear formularios para varios destinos</h2><p className="mt-1 text-sm text-slate-600">Escribe cada título una sola vez. Se repetirá en todos los eventos o programaciones elegidos.</p></div><button aria-label="Cerrar" disabled={creating} className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50" onClick={onClose} type="button"><X className="h-5 w-5" /></button></header>

      <fieldset className="mt-5"><legend className="text-sm font-semibold text-slate-800">¿Dónde crear los formularios?</legend><div className="mt-2 grid gap-2 sm:grid-cols-2">
        <label className={`cursor-pointer rounded-xl border p-3 ${scope === "EVENT" ? "border-emerald-500 bg-emerald-50" : "border-slate-200"}`}><input className="mr-2 accent-emerald-700" checked={scope === "EVENT"} name="bulk-scope" onChange={() => { setScope("EVENT"); setExistingKeys(null); setResult(null); }} type="radio" />Evento completo<p className="ml-6 text-xs text-slate-600">Un formulario por tipo en cada evento.</p></label>
        <label className={`cursor-pointer rounded-xl border p-3 ${scope === "SESSION" ? "border-emerald-500 bg-emerald-50" : "border-slate-200"}`}><input className="mr-2 accent-emerald-700" checked={scope === "SESSION"} name="bulk-scope" onChange={() => { setScope("SESSION"); setExistingKeys(null); setResult(null); }} type="radio" />Programaciones<p className="ml-6 text-xs text-slate-600">Crea formularios ligados solo a las programaciones elegidas.</p></label>
      </div></fieldset>

      <fieldset className="mt-5"><legend className="text-sm font-semibold text-slate-800">Selecciona los eventos</legend><div className="mt-2 grid max-h-44 gap-2 overflow-y-auto rounded-xl border border-slate-200 p-2 sm:grid-cols-2">{events.map((event) => <label key={event.id} className="flex cursor-pointer items-start gap-2 rounded-lg p-2 text-sm hover:bg-slate-50"><input checked={selectedEventIds.includes(event.id)} className="mt-0.5 accent-emerald-700" onChange={() => toggleEvent(event.id)} type="checkbox" /><span className="min-w-0"><span className="block font-medium text-slate-900">{event.name}</span><span className="block truncate text-xs text-slate-600">Cliente: {event.client?.business_name || "No informado"}</span><span className="block text-xs text-slate-500">{eventDate(event)}</span></span></label>)}{!events.length ? <p className="p-3 text-sm text-slate-500">Cargando eventos o no hay eventos disponibles.</p> : null}</div><div className="mt-2 flex gap-2"><Button size="sm" type="button" variant="secondary" onClick={() => { setSelectedEventIds(events.map((event) => event.id)); setExistingKeys(null); setResult(null); }}>Seleccionar todos</Button><Button size="sm" type="button" variant="ghost" onClick={() => { setSelectedEventIds([]); setSelectedSessionIds([]); setExistingKeys(null); setResult(null); }}>Limpiar</Button></div></fieldset>

      {scope === "SESSION" ? <fieldset className="mt-5"><legend className="text-sm font-semibold text-slate-800">Selecciona las programaciones</legend><div className="mt-2 max-h-48 space-y-1 overflow-y-auto rounded-xl border border-slate-200 p-2">{sessionsLoading ? <p className="p-3 text-sm text-slate-500">Cargando programaciones…</p> : sessions.map((session) => <label key={session.id} className="flex cursor-pointer items-center gap-2 rounded-lg p-2 text-sm hover:bg-slate-50"><input checked={selectedSessionIds.includes(session.id)} className="accent-emerald-700" onChange={() => toggleSession(session.id)} type="checkbox" /><span className="min-w-0"><span className="block font-medium">{session.name}</span><span className="block text-xs text-slate-500">{(session as EventSession & { event_name?: string }).event_name} · {events.find((event) => event.id === session.event_id)?.client?.business_name || "Cliente no informado"}</span></span>{session.session_date ? <span className="ml-auto shrink-0 text-xs text-slate-500">{session.session_date}</span> : null}</label>)}{!sessionsLoading && !sessions.length ? <p className="p-3 text-sm text-slate-500">Selecciona al menos un evento con programaciones activas.</p> : null}</div></fieldset> : null}

      <fieldset className="mt-5"><legend className="text-sm font-semibold text-slate-800">Tipos y títulos (se reutilizan en todo el lote)</legend><div className="mt-2 space-y-2">{bulkTypes.map(({ type, label }) => <div key={type} className={`grid gap-2 rounded-xl border p-3 sm:grid-cols-[minmax(150px,0.8fr)_1.2fr] sm:items-center ${selectedTypes.includes(type) ? "border-emerald-200 bg-emerald-50/40" : "border-slate-200"}`}><label className="flex items-center gap-2 text-sm font-semibold"><input checked={selectedTypes.includes(type)} className="accent-emerald-700" onChange={() => toggleType(type)} type="checkbox" />{label}</label><Input aria-label={`Título para ${label}`} disabled={!selectedTypes.includes(type)} maxLength={180} value={titles[type]} onChange={(event) => setTitles((current) => ({ ...current, [type]: event.target.value }))} /></div>)}</div></fieldset>

      <div className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="font-semibold text-slate-900">Resumen</p><p className="mt-1 text-sm text-slate-600">{targets.length} {scope === "EVENT" ? "evento(s)" : "programación(es)"} × {selectedTypes.length} tipo(s) = <strong>{total} formulario(s)</strong>{existingKeys ? <> · {existingKeys.size} ya existen y se omitirán · <strong>{remaining} por crear</strong></> : null}</p>{targets.length && selectedTypes.length ? <p className="mt-1 text-xs text-slate-500">Los nuevos formularios quedarán como borradores. No se publican ni se reemplazan formularios existentes.</p> : null}{creating ? <div className="mt-3"><div className="mb-1 flex justify-between text-xs text-slate-600"><span>Procesando lote…</span><span>{progress}/{total}</span></div><div className="h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full bg-emerald-600 transition-all" style={{ width: `${total ? progress / total * 100 : 0}%` }} /></div></div> : null}</div>

      {error ? <p role="alert" className="mt-3 flex gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-800"><AlertCircle className="h-4 w-4 shrink-0" />{error}</p> : null}
      {result ? <div className="mt-3 rounded-lg border border-slate-200 p-3 text-sm"><p className="font-semibold text-slate-900">Lote procesado: {result.created.length} creados, {result.skipped.length} omitidos, {result.failed.length} con error.</p>{result.failed.length ? <><ul className="mt-2 list-inside list-disc text-rose-700">{result.failed.map((message, index) => <li key={`${index}-${message}`}>{message}</li>)}</ul><Button className="mt-2" size="sm" type="button" variant="secondary" onClick={() => { setResult(null); setExistingKeys(null); }}>Revisar e intentar de nuevo</Button></> : null}{result.skipped.length ? <p className="mt-1 text-xs text-slate-500">Los omitidos ya tenían un formulario de ese tipo en ese destino.</p> : null}</div> : null}

      <footer className="mt-5 flex flex-wrap justify-end gap-2"><Button type="button" variant="secondary" disabled={creating} onClick={onClose}>{result ? "Cerrar" : "Cancelar"}</Button>{!existingKeys && !result ? <Button type="button" disabled={checking || creating || !total || selectedTypes.some((type) => !titles[type].trim()) || (scope === "SESSION" && sessionsLoading)} onClick={() => void reviewBatch()}>{checking ? <><LoaderCircle className="h-4 w-4 animate-spin" />Revisando…</> : "Revisar lote"}</Button> : null}{existingKeys && !result ? <Button type="button" onClick={() => void createBatch()} disabled={creating || !remaining}>{creating ? <><LoaderCircle className="h-4 w-4 animate-spin" />Creando {progress}/{total}…</> : <><Check className="h-4 w-4" />Crear {remaining} formulario(s)</>}</Button> : null}</footer>
    </section>
  </div>;
}
