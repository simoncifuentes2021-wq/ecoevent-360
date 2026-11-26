"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { AlertCircle, BellRing, CalendarClock, Check, CheckCircle2, ChevronDown, Clock3, History, ListTodo, LoaderCircle, Pencil, Plus, RefreshCw, Save, UserRound, X } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { getEvents } from "@/lib/api/events";
import { createFieldChecklistItem, getFieldChecklist, getFieldChecklistEmailStatus, getFieldChecklistHistory, getFieldChecklistPeople, updateFieldChecklistItem } from "@/lib/api/fieldChecklists";
import { useAuth } from "@/hooks/useAuth";
import type { Event } from "@/types/event";
import type { FieldChecklistHistory, FieldChecklistItem, FieldChecklistItemCreate, FieldChecklistPerson, FieldChecklistStatus } from "@/types/fieldChecklist";

const statusLabel: Record<FieldChecklistStatus, string> = {
  PENDING: "Pendiente", IN_PROGRESS: "En curso", COMPLETED: "Completada", BLOCKED: "Con problema",
};
const statusStyle: Record<FieldChecklistStatus, string> = {
  PENDING: "bg-slate-100 text-slate-700", IN_PROGRESS: "bg-blue-50 text-blue-700",
  COMPLETED: "bg-emerald-50 text-emerald-700", BLOCKED: "bg-rose-50 text-rose-700",
};

function asUtc(value: string) {
  return value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`;
}

function displayDate(value: string) {
  return new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Santiago" }).format(new Date(asUtc(value)));
}

function dayKey(value: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Santiago", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date(asUtc(value)));
  const part = (type: string) => parts.find((item) => item.type === type)?.value || "00";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function dayLabel(value: string) {
  const date = new Date(`${value}T12:00:00Z`);
  const label = new Intl.DateTimeFormat("es-CL", {
    weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "America/Santiago",
  }).format(date);
  return label.charAt(0).toLocaleUpperCase("es-CL") + label.slice(1);
}

function formatEventDate(value: string) {
  const date = new Date(`${value.slice(0, 10)}T12:00:00Z`);
  return new Intl.DateTimeFormat("es-CL", { day: "numeric", month: "long", year: "numeric", timeZone: "America/Santiago" }).format(date);
}

function eventDateRange(event: Event) {
  const start = formatEventDate(event.start_date);
  const end = formatEventDate(event.end_date);
  return start === end ? start : `${start} al ${end}`;
}

function toLocalInput(value?: string | null) {
  if (!value) return "";
  const date = new Date(asUtc(value));
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Santiago", year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(date);
  const part = (type: string) => parts.find((item) => item.type === type)?.value || "00";
  return `${part("year")}-${part("month")}-${part("day")}T${part("hour")}:${part("minute")}`;
}

function localToIso(value: string) {
  return new Date(value).toISOString();
}

function isOverdue(item: FieldChecklistItem) {
  return item.status !== "COMPLETED" && new Date(asUtc(item.due_at)).getTime() < Date.now();
}

export function FieldChecklistPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const isSuperAdmin = user?.role === "SUPER_ADMIN";
  const [events, setEvents] = useState<Event[]>([]);
  const [eventId, setEventId] = useState("");
  const [people, setPeople] = useState<FieldChecklistPerson[]>([]);
  const [ownerId, setOwnerId] = useState("");
  const [items, setItems] = useState<FieldChecklistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [historyFor, setHistoryFor] = useState<string | null>(null);
  const [history, setHistory] = useState<FieldChecklistHistory[]>([]);
  const [emailConfigured, setEmailConfigured] = useState<boolean | null>(null);
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [statusNote, setStatusNote] = useState("");
  const [filter, setFilter] = useState<"ALL" | "PENDING" | "COMPLETED">("ALL");
  const formOpen = showForm || Boolean(editingId);

  useEffect(() => {
    getEvents({ limit: 100, page: 1 })
      .then((response) => {
        setEvents(response.items);
        setEventId((current) => current || response.items[0]?.id || "");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "No se pudieron cargar los eventos."))
      .finally(() => setLoading(false));
  }, []);

  const load = useCallback(async (quiet = false) => {
    if (!eventId) return;
    if (quiet) setRefreshing(true);
    else setLoading(true);
    setError(null);
    try {
      const [personList, itemList, emailState] = await Promise.all([
        getFieldChecklistPeople(eventId), getFieldChecklist(eventId, isSuperAdmin ? ownerId || undefined : undefined), getFieldChecklistEmailStatus(),
      ]);
      setPeople(personList);
      setEmailConfigured(emailState.configured);
      if (isSuperAdmin && !ownerId && personList.length) setOwnerId(personList[0].id);
      setItems(itemList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el checklist.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [eventId, isSuperAdmin, ownerId]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (!eventId) return;
    const timer = window.setInterval(() => { void load(true); }, isSuperAdmin ? 30_000 : 60_000);
    return () => window.clearInterval(timer);
  }, [isSuperAdmin, eventId, load]);

  useEffect(() => {
    if (!formOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && !saving) resetForm();
    }
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [formOpen, saving]);

  const visibleItems = useMemo(() => items.filter((item) => {
    if (filter === "PENDING") return item.status !== "COMPLETED";
    if (filter === "COMPLETED") return item.status === "COMPLETED";
    return true;
  }), [items, filter]);
  const dailyGroups = useMemo(() => {
    const groups = new Map<string, FieldChecklistItem[]>();
    for (const item of visibleItems) {
      const key = dayKey(item.due_at);
      groups.set(key, [...(groups.get(key) || []), item]);
    }
    return Array.from(groups.entries()).sort(([first], [second]) => first.localeCompare(second));
  }, [visibleItems]);
  const completedCount = items.filter((item) => item.status === "COMPLETED").length;
  const overdueCount = items.filter(isOverdue).length;
  const selectedEvent = events.find((event) => event.id === eventId);
  const selectedPerson = people.find((person) => person.id === (isSuperAdmin ? ownerId : user?.id));

  function resetForm() {
    setTitle(""); setDetails(""); setDueAt(""); setStatusNote("");
    setShowForm(false); setEditingId(null);
  }

  function startEdit(item: FieldChecklistItem) {
    setEditingId(item.id); setShowForm(false); setTitle(item.title); setDetails(item.details || "");
    setDueAt(toLocalInput(item.due_at)); setStatusNote(item.status_note || "");
  }

  async function saveItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!eventId || !title.trim() || !dueAt) return;
    setSaving(true);
    try {
      if (editingId) {
        await updateFieldChecklistItem(editingId, { title: title.trim(), details: details.trim() || null, due_at: localToIso(dueAt), status_note: statusNote.trim() || null });
        toast({ tone: "success", title: "Actividad actualizada" });
      } else {
        const data: FieldChecklistItemCreate = {
          title: title.trim(), details: details.trim() || null, due_at: localToIso(dueAt),
          ...(isSuperAdmin && ownerId ? { user_id: ownerId } : {}),
        };
        await createFieldChecklistItem(eventId, data);
        toast({ tone: "success", title: "Actividad agregada a tu checklist" });
      }
      resetForm(); await load(true);
    } catch (err) {
      toast({ tone: "error", title: "No se pudo guardar", description: err instanceof Error ? err.message : "Intenta nuevamente." });
    } finally { setSaving(false); }
  }

  async function changeStatus(item: FieldChecklistItem, status: FieldChecklistStatus) {
    try {
      await updateFieldChecklistItem(item.id, { status });
      await load(true);
    } catch (err) {
      toast({ tone: "error", title: "No se pudo actualizar el estado", description: err instanceof Error ? err.message : "Intenta nuevamente." });
    }
  }

  async function toggleHistory(itemId: string) {
    if (historyFor === itemId) { setHistoryFor(null); return; }
    setHistoryFor(itemId);
    try { setHistory(await getFieldChecklistHistory(itemId)); }
    catch (err) { toast({ tone: "error", title: "No se pudo cargar el historial", description: err instanceof Error ? err.message : "Intenta nuevamente." }); }
  }

  if (loading && events.length === 0) return <LoadingState label="Cargando checklist de terreno..." />;

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Organización personal en terreno</p>
          <h1 className="mt-1 text-2xl font-bold text-slate-950">Mi checklist</h1>
          <p className="mt-1 text-sm text-slate-600">Tus actividades, ordenadas por la hora exacta que programaste.</p>
        </div>
        <Button onClick={() => { resetForm(); setShowForm(true); }} disabled={!eventId}><Plus className="h-4 w-4" />Agregar actividad</Button>
      </header>

      <Card><CardContent className="grid gap-4 md:grid-cols-2">
        <label className="text-sm font-semibold text-slate-700">Evento
          <select className="mt-1 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal" value={eventId} onChange={(e) => { setEventId(e.target.value); setOwnerId(""); resetForm(); }}>
            <option value="">Selecciona un evento</option>
            {events.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}
          </select>
          {selectedEvent ? <span className="mt-1 block text-xs font-normal text-slate-500">Período: {eventDateRange(selectedEvent)}</span> : null}
        </label>
        {isSuperAdmin ? <label className="text-sm font-semibold text-slate-700">Checklist de la persona
          <select className="mt-1 h-11 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal" value={ownerId} onChange={(e) => setOwnerId(e.target.value)}>
            {people.map((person) => <option key={person.id} value={person.id}>{person.full_name}</option>)}
          </select>
        </label> : <div className="flex items-end text-sm text-slate-600"><UserRound className="mr-2 h-4 w-4 text-emerald-700" />Lista personal de {user?.full_name}</div>}
      </CardContent></Card>

      {isSuperAdmin ? <div className="flex items-center justify-between rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-950">
        <span>Supervisión en vivo: vista actualizada automáticamente cada 30 segundos.</span>
        <Button variant="ghost" size="sm" onClick={() => void load(true)} disabled={refreshing}><RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />Actualizar</Button>
      </div> : null}

      {error ? <ErrorState message={error} onRetry={() => void load()} /> : null}
      {emailConfigured === false ? <div role="alert" className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"><BellRing className="mt-0.5 h-4 w-4 shrink-0" /><p><strong>Los recordatorios por correo aún no están activados en este entorno.</strong> Configura RESEND_API_KEY en la API y reiníciala para que los avisos se envíen.</p></div> : null}

      {formOpen ? <div className="fixed inset-0 z-[100] flex items-center justify-center overflow-y-auto bg-slate-950/55 p-3 backdrop-blur-sm sm:p-6" role="dialog" aria-modal="true" aria-labelledby="field-checklist-form-title" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) resetForm(); }}>
        <section className="my-auto w-full max-w-2xl rounded-2xl border border-white/70 bg-white shadow-2xl">
        <CardContent className="max-h-[90vh] overflow-y-auto p-5 sm:p-7">
        <form className="space-y-4" onSubmit={saveItem}>
          <div className="flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-wider text-emerald-700">Checklist personal</p><h2 id="field-checklist-form-title" className="mt-1 text-xl font-bold text-slate-950">{editingId ? "Editar actividad" : "Nueva actividad"}</h2></div><button type="button" onClick={resetForm} disabled={saving} aria-label="Cerrar ventana" className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 disabled:opacity-50"><X className="h-5 w-5" /></button></div>
          {isSuperAdmin && !editingId ? <p className="text-sm text-slate-600">Se agregará a la lista personal de <strong>{selectedPerson?.full_name || "la persona seleccionada"}</strong>.</p> : null}
          <label className="block text-sm font-medium text-slate-700">¿Qué tienes que hacer?<input required maxLength={180} autoFocus className="mt-1 h-11 w-full rounded-lg border border-slate-200 px-3" placeholder="Ej. Revisar que los puntos estén listos" value={title} onChange={(e) => setTitle(e.target.value)} /></label>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="block text-sm font-medium text-slate-700">Día y hora exacta
              <input required type="datetime-local" className="mt-1 h-11 w-full rounded-lg border border-slate-200 bg-white px-3" value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
              <span className="mt-1 block text-xs text-slate-500">El recordatorio se enviará cuando llegue esta hora si sigue pendiente.</span>
            </label>
            {editingId ? <label className="block text-sm font-medium text-slate-700">Nota del estado (opcional)<textarea maxLength={2000} className="mt-1 min-h-11 w-full rounded-lg border border-slate-200 px-3 py-2" placeholder="Explica el problema o deja una actualización" value={statusNote} onChange={(e) => setStatusNote(e.target.value)} /></label> : null}
          </div>
          <label className="block text-sm font-medium text-slate-700">Detalle o instrucciones (opcional)<textarea maxLength={4000} className="mt-1 min-h-20 w-full rounded-lg border border-slate-200 px-3 py-2" placeholder="Agrega solo lo necesario" value={details} onChange={(e) => setDetails(e.target.value)} /></label>
          <div className="flex justify-end gap-2"><Button type="button" variant="secondary" onClick={resetForm}>Cancelar</Button><Button type="submit" disabled={saving || !dueAt}>{saving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}{saving ? "Guardando..." : "Guardar actividad"}</Button></div>
        </form>
        </CardContent></section>
      </div> : null}

      <div className="grid gap-3 sm:grid-cols-3">
        <Card><CardContent className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-slate-100 text-slate-700"><ListTodo className="h-5 w-5" /></span><div><p className="text-xs text-slate-500">Actividades</p><p className="text-xl font-bold">{items.length}</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><CheckCircle2 className="h-5 w-5" /></span><div><p className="text-xs text-slate-500">Completadas</p><p className="text-xl font-bold">{completedCount}</p></div></CardContent></Card>
        <Card><CardContent className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-rose-50 text-rose-700"><AlertCircle className="h-5 w-5" /></span><div><p className="text-xs text-slate-500">Atrasadas</p><p className="text-xl font-bold">{overdueCount}</p></div></CardContent></Card>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-lg font-bold text-slate-900">{selectedPerson?.full_name || "Tus actividades"}</h2><p className="text-sm text-slate-500">{selectedEvent?.name || "Elige un evento para ver tu lista"}</p>{selectedEvent ? <p className="mt-1 text-xs font-medium text-emerald-800">{eventDateRange(selectedEvent)}</p> : null}</div><div className="flex gap-1 rounded-lg bg-slate-100 p-1">{([ ["ALL", "Todas"], ["PENDING", "Pendientes"], ["COMPLETED", "Completadas"] ] as const).map(([key, label]) => <button key={key} onClick={() => setFilter(key)} className={`rounded-md px-3 py-1.5 text-xs font-semibold ${filter === key ? "bg-white text-emerald-800 shadow-sm" : "text-slate-600"}`}>{label}</button>)}</div></div>

      {!eventId ? <Card><CardContent className="py-12 text-center text-slate-500">No hay eventos disponibles para tu cuenta.</CardContent></Card> : visibleItems.length === 0 ? <Card><CardContent className="py-12 text-center"><span className="mx-auto grid h-12 w-12 place-items-center rounded-2xl bg-emerald-50 text-emerald-700"><Check className="h-6 w-6" /></span><h3 className="mt-3 font-semibold text-slate-900">{filter === "ALL" ? "Tu checklist está listo para empezar" : "No hay actividades en este filtro"}</h3><p className="mt-1 text-sm text-slate-500">Agrega una actividad y programa el día y la hora exactos.</p><Button className="mt-4" size="sm" onClick={() => setShowForm(true)}><Plus className="h-4 w-4" />Agregar actividad</Button></CardContent></Card> : <div className="space-y-6">{dailyGroups.map(([date, dayItems]) => <section key={date} className="space-y-3"><div className="flex items-center justify-between border-b border-slate-200 pb-2"><h3 className="font-semibold text-slate-800">{dayLabel(date)}</h3><span className="text-xs text-slate-500">{dayItems.length} {dayItems.length === 1 ? "actividad" : "actividades"}</span></div><div className="space-y-3">{dayItems.map((item) => <Card key={item.id} className={isOverdue(item) ? "border-rose-200" : ""}><CardContent className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-semibold text-slate-900">{item.title}</h3><span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${statusStyle[item.status]}`}>{statusLabel[item.status]}</span>{isOverdue(item) ? <span className="rounded-full bg-rose-50 px-2.5 py-1 text-xs font-semibold text-rose-700">Atrasada</span> : null}</div>
            <p className="mt-2 flex items-center gap-1.5 text-sm text-slate-600"><CalendarClock className="h-4 w-4 text-emerald-700" />{displayDate(item.due_at)}</p>
            {item.details ? <p className="mt-2 whitespace-pre-wrap text-sm text-slate-600">{item.details}</p> : null}
            {isSuperAdmin ? <p className="mt-2 text-xs text-slate-500">{item.owner_email}</p> : null}
            {item.status_note ? <p className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{item.status_note}</p> : null}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {item.status !== "COMPLETED" ? <select aria-label="Estado de actividad" value={item.status} onChange={(e) => void changeStatus(item, e.target.value as FieldChecklistStatus)} className="h-9 rounded-lg border border-slate-200 bg-white px-2 text-sm"><option value="PENDING">Pendiente</option><option value="IN_PROGRESS">En curso</option><option value="COMPLETED">Completada</option><option value="BLOCKED">Con problema</option></select> : <Button size="sm" variant="secondary" onClick={() => void changeStatus(item, "PENDING")}>Reabrir</Button>}
            <Button size="sm" variant="secondary" onClick={() => startEdit(item)} aria-label="Editar actividad"><Pencil className="h-4 w-4" />Editar</Button>
            <Button size="sm" variant="ghost" onClick={() => void toggleHistory(item.id)} aria-expanded={historyFor === item.id}><History className="h-4 w-4" />Historial<ChevronDown className={`h-3 w-3 transition ${historyFor === item.id ? "rotate-180" : ""}`} /></Button>
          </div>
        </div>
        {item.reminder_sent_at ? <p className="flex items-center gap-1.5 text-xs text-amber-700"><BellRing className="h-3.5 w-3.5" />Recordatorio enviado {displayDate(item.reminder_sent_at)}</p> : item.reminder_failed ? <p className="flex items-center gap-1.5 text-xs text-rose-700"><AlertCircle className="h-3.5 w-3.5" />No se pudo enviar el correo. Revisa la configuración del servicio de correo.</p> : item.status !== "COMPLETED" && isOverdue(item) ? <p className="flex items-center gap-1.5 text-xs text-amber-700"><Clock3 className="h-3.5 w-3.5" />Se enviará un recordatorio por correo automáticamente.</p> : null}
        {historyFor === item.id ? <div className="border-t border-slate-100 pt-3">{history.length ? <ol className="space-y-2">{history.map((entry) => <li key={entry.id} className="text-xs text-slate-600"><span className="font-semibold text-slate-800">{entry.actor_name}</span> · {entry.description} · {displayDate(entry.created_at)}</li>)}</ol> : <p className="text-sm text-slate-500">Sin movimientos todavía.</p>}</div> : null}
      </CardContent></Card>)}</div></section>)}</div>}
      <p className="flex items-center gap-2 text-xs text-slate-500"><BellRing className="h-4 w-4 text-emerald-700" />Los avisos por correo están activos: se envían cuando llega la hora programada y la actividad sigue pendiente.</p>
    </div>
  );
}
