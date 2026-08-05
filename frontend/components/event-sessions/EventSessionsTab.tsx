"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Archive, ArrowDown, ArrowUp, Copy, Eye, Pencil, Plus, RotateCcw, Trash2 } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { ShowOperationsPanel } from "@/components/event-sessions/ShowOperationsPanel";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  archiveEventSession, createEventSession, deleteEventSession, duplicateEventSession,
  getEventSessions, reorderEventSessions, restoreEventSession, transitionEventSession, updateEventSession
} from "@/lib/api/eventSessions";
import { getEventStaff } from "@/lib/api/staff";
import type { EventSession, EventSessionCreate, EventSessionStatus } from "@/types/eventSession";
import type { UserRole } from "@/types/roles";
import type { EventStaff } from "@/types/staff";

const statusLabels: Record<EventSessionStatus, string> = { PLANNED: "Planificado", READY: "Listo", IN_PROGRESS: "En curso", COMPLETED: "Completado", CANCELLED: "Cancelado" };
const transitions: Record<EventSessionStatus, EventSessionStatus[]> = { PLANNED: ["READY", "CANCELLED"], READY: ["PLANNED", "IN_PROGRESS", "CANCELLED"], IN_PROGRESS: ["COMPLETED", "CANCELLED"], COMPLETED: [], CANCELLED: ["PLANNED"] };
const emptyForm: EventSessionCreate = { name: "", description: "", session_date: null, start_time: null, end_time: null, venue_name: "", stage_name: "", expected_attendees: 0, real_attendees: null, responsible_id: null, internal_notes: "" };

export function EventSessionsTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const { toast } = useToast();
  const [items, setItems] = useState<EventSession[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [editing, setEditing] = useState<EventSession | "new" | null>(null);
  const [detail, setDetail] = useState<EventSession | null>(null);
  const [confirm, setConfirm] = useState<{ action: "archive" | "delete"; item: EventSession } | null>(null);
  const [form, setForm] = useState<EventSessionCreate>(emptyForm);
  const canManage = role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";

  const staffNames = useMemo(() => new Map(staff.map((item) => [item.user_id, item.user?.full_name || item.user?.email || "Personal asignado"])), [staff]);
  const activeItems = useMemo(() => items.filter((item) => !item.archived_at), [items]);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [sessionData, staffData] = await Promise.all([getEventSessions(eventId, showArchived), getEventStaff(eventId).catch(() => [])]);
      setItems(sessionData); setStaff(staffData);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "No se pudieron cargar los shows."); }
    finally { setLoading(false); }
  }, [eventId, showArchived]);
  useEffect(() => { void load(); }, [load]);

  function openEditor(item?: EventSession) {
    if (item) setForm({ name: item.name, description: item.description || "", session_date: item.session_date || null, start_time: item.start_time?.slice(0, 5) || null, end_time: item.end_time?.slice(0, 5) || null, venue_name: item.venue_name || "", stage_name: item.stage_name || "", expected_attendees: item.expected_attendees, real_attendees: item.real_attendees ?? null, responsible_id: item.responsible_id || null, internal_notes: item.internal_notes || "", sort_order: item.sort_order });
    else setForm(emptyForm);
    setEditing(item || "new");
  }

  async function save() {
    setSaving(true);
    try {
      const payload = { ...form, name: form.name.trim(), description: form.description?.trim() || null, venue_name: form.venue_name?.trim() || null, stage_name: form.stage_name?.trim() || null, internal_notes: form.internal_notes?.trim() || null };
      const result = editing === "new" ? await createEventSession(eventId, payload) : await updateEventSession(editing!.id, payload);
      setEditing(null); await load();
      toast({ tone: "success", title: editing === "new" ? "Show creado" : "Show actualizado", description: result.overlap_warning ? "Atención: se superpone con otro show del mismo recinto o escenario." : undefined });
    } catch (cause) { toast({ tone: "error", title: "No se pudo guardar", description: cause instanceof Error ? cause.message : undefined }); }
    finally { setSaving(false); }
  }

  async function changeStatus(item: EventSession, status: EventSessionStatus) {
    try { await transitionEventSession(item.id, status); await load(); toast({ tone: "success", title: `Estado cambiado a ${statusLabels[status]}` }); }
    catch (cause) { toast({ tone: "error", title: "No se pudo cambiar el estado", description: cause instanceof Error ? cause.message : undefined }); }
  }

  async function duplicate(item: EventSession) {
    try { const copy = await duplicateEventSession(item.id); await load(); toast({ tone: "success", title: "Show duplicado", description: copy.overlap_warning ? "La copia conserva el horario y presenta una superposición." : undefined }); }
    catch (cause) { toast({ tone: "error", title: "No se pudo duplicar", description: cause instanceof Error ? cause.message : undefined }); }
  }

  async function move(index: number, direction: -1 | 1) {
    const active = items.filter((item) => !item.archived_at); const target = index + direction;
    if (target < 0 || target >= active.length) return;
    [active[index], active[target]] = [active[target], active[index]];
    try { setItems(await reorderEventSessions(eventId, active.map((item) => item.id))); }
    catch (cause) { toast({ tone: "error", title: "No se pudo reordenar", description: cause instanceof Error ? cause.message : undefined }); }
  }

  async function confirmAction() {
    if (!confirm) return; setSaving(true);
    try {
      if (confirm.action === "archive") await archiveEventSession(confirm.item.id); else await deleteEventSession(confirm.item.id);
      toast({ tone: "success", title: confirm.action === "archive" ? "Show archivado" : "Show eliminado" }); setConfirm(null); await load();
    } catch (cause) { toast({ tone: "error", title: "No se pudo completar la acción", description: cause instanceof Error ? cause.message : undefined }); }
    finally { setSaving(false); }
  }

  return <div className="space-y-4">
    <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between"><div><h2 className="text-xl font-bold text-slate-950">Programación</h2><p className="text-sm text-slate-600">Shows, jornadas o funciones asociadas al evento.</p></div><div className="flex gap-2"><Button type="button" variant="secondary" onClick={() => setShowArchived((value) => !value)}>{showArchived ? "Ocultar archivados" : "Ver archivados"}</Button>{canManage ? <Button onClick={() => openEditor()} type="button"><Plus className="h-4 w-4" />Crear show</Button> : null}</div></div>
    {loading ? <LoadingState label="Cargando programación..." /> : null}{error ? <ErrorState message={error} onRetry={load} /> : null}
    {!loading && !error ? <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{items.map((item) => <article className={`rounded-lg border bg-white p-4 shadow-sm ${item.archived_at ? "opacity-60" : ""}`} key={item.id}>
      <div className="flex items-start justify-between gap-2"><div><h3 className="font-bold text-slate-950">{item.name}</h3><p className="mt-1 text-sm text-slate-600">{[item.session_date, item.start_time?.slice(0, 5), item.end_time ? `– ${item.end_time.slice(0, 5)}` : null].filter(Boolean).join(" ") || "Sin fecha definida"}</p></div><span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold">{item.archived_at ? "Archivado" : statusLabels[item.status]}</span></div>
      <p className="mt-2 text-sm text-slate-600">{[item.venue_name, item.stage_name].filter(Boolean).join(" · ") || "Sin recinto"}</p><p className="mt-2 text-xs text-slate-500">Asistentes: {item.real_attendees ?? "—"} reales / {item.expected_attendees} esperados</p>{item.responsible_id ? <p className="mt-1 text-xs text-slate-500">Responsable: {staffNames.get(item.responsible_id) || "Asignado"}</p> : null}
      {item.overlap_warning ? <p className="mt-3 flex gap-1 text-xs font-semibold text-amber-700"><AlertTriangle className="h-4 w-4" />Horario superpuesto</p> : null}
      <div className="mt-4 flex flex-wrap gap-2"><Button variant="secondary" type="button" onClick={() => setDetail(item)}><Eye className="h-4 w-4" />Detalle</Button>{canManage && !item.archived_at ? <><Button variant="secondary" type="button" onClick={() => openEditor(item)}><Pencil className="h-4 w-4" /></Button><Button variant="secondary" type="button" onClick={() => void duplicate(item)}><Copy className="h-4 w-4" /></Button><Button variant="secondary" disabled={activeItems.findIndex((value) => value.id === item.id) === 0} type="button" onClick={() => void move(activeItems.findIndex((value) => value.id === item.id), -1)}><ArrowUp className="h-4 w-4" /></Button><Button variant="secondary" disabled={activeItems.findIndex((value) => value.id === item.id) === activeItems.length - 1} type="button" onClick={() => void move(activeItems.findIndex((value) => value.id === item.id), 1)}><ArrowDown className="h-4 w-4" /></Button><Button variant="secondary" type="button" onClick={() => setConfirm({ action: "archive", item })}><Archive className="h-4 w-4" /></Button><Button variant="secondary" type="button" onClick={() => setConfirm({ action: "delete", item })}><Trash2 className="h-4 w-4" /></Button></> : null}{canManage && item.archived_at ? <Button type="button" variant="secondary" onClick={async () => { await restoreEventSession(item.id); await load(); }}><RotateCcw className="h-4 w-4" />Restaurar</Button> : null}</div>
    </article>)}{!items.length ? <p className="text-sm text-slate-500">Aún no hay shows creados.</p> : null}</div> : null}
    {editing ? <SessionEditor form={form} saving={saving} staff={staff} title={editing === "new" ? "Crear show o sesión" : "Editar show"} onChange={setForm} onClose={() => setEditing(null)} onSave={() => void save()} /> : null}
    {detail ? <SessionDetail eventId={eventId} item={detail} role={role} staff={staff} responsible={detail.responsible_id ? staffNames.get(detail.responsible_id) : undefined} canManage={canManage && !detail.archived_at} onClose={() => setDetail(null)} onTransition={(status) => { void changeStatus(detail, status); setDetail(null); }} /> : null}
    <ConfirmDialog open={Boolean(confirm)} loading={saving} title={confirm?.action === "delete" ? "Eliminar show" : "Archivar show"} description={confirm?.action === "delete" ? "Sólo se eliminará si no contiene formularios, respuestas, Bike Zone ni códigos QR. Si tiene datos, debes archivarlo." : "El show dejará de aparecer en la programación activa y conservará toda su información."} confirmLabel={confirm?.action === "delete" ? "Eliminar" : "Archivar"} onClose={() => setConfirm(null)} onConfirm={() => void confirmAction()} />
  </div>;
}

function SessionEditor({ form, saving, staff, title, onChange, onClose, onSave }: { form: EventSessionCreate; saving: boolean; staff: EventStaff[]; title: string; onChange: (value: EventSessionCreate) => void; onClose: () => void; onSave: () => void }) {
  return <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/45 p-4"><form className="my-6 w-full max-w-2xl rounded-lg bg-white p-5 shadow-2xl" onSubmit={(event) => { event.preventDefault(); onSave(); }}><h3 className="text-lg font-bold">{title}</h3><div className="mt-4 grid gap-3 md:grid-cols-2">
    <label className="grid gap-1 text-sm font-semibold md:col-span-2">Nombre<Input required maxLength={180} value={form.name} onChange={(event) => onChange({ ...form, name: event.target.value })} /></label>
    <label className="grid gap-1 text-sm font-semibold md:col-span-2">Descripción<textarea className="min-h-20 rounded-md border p-3 font-normal" value={form.description || ""} onChange={(event) => onChange({ ...form, description: event.target.value })} /></label>
    <label className="grid gap-1 text-sm font-semibold">Fecha<Input type="date" value={form.session_date || ""} onChange={(event) => onChange({ ...form, session_date: event.target.value || null })} /></label><span />
    <label className="grid gap-1 text-sm font-semibold">Inicio<Input type="time" value={form.start_time || ""} onChange={(event) => onChange({ ...form, start_time: event.target.value || null })} /></label><label className="grid gap-1 text-sm font-semibold">Término<Input type="time" value={form.end_time || ""} onChange={(event) => onChange({ ...form, end_time: event.target.value || null })} /></label>
    <label className="grid gap-1 text-sm font-semibold">Recinto<Input value={form.venue_name || ""} onChange={(event) => onChange({ ...form, venue_name: event.target.value })} /></label><label className="grid gap-1 text-sm font-semibold">Escenario<Input value={form.stage_name || ""} onChange={(event) => onChange({ ...form, stage_name: event.target.value })} /></label>
    <label className="grid gap-1 text-sm font-semibold">Asistentes esperados<Input min={0} type="number" value={form.expected_attendees ?? 0} onChange={(event) => onChange({ ...form, expected_attendees: Number(event.target.value) })} /></label><label className="grid gap-1 text-sm font-semibold">Asistentes reales<Input min={0} type="number" value={form.real_attendees ?? ""} onChange={(event) => onChange({ ...form, real_attendees: event.target.value === "" ? null : Number(event.target.value) })} /></label>
    <label className="grid gap-1 text-sm font-semibold md:col-span-2">Responsable<select className="h-10 rounded-md border bg-white px-3 font-normal" value={form.responsible_id || ""} onChange={(event) => onChange({ ...form, responsible_id: event.target.value || null })}><option value="">Sin responsable</option>{staff.map((item) => <option key={item.user_id} value={item.user_id}>{item.user?.full_name || item.user?.email || item.user_id}</option>)}</select></label>
    <label className="grid gap-1 text-sm font-semibold md:col-span-2">Notas internas<textarea className="min-h-20 rounded-md border p-3 font-normal" value={form.internal_notes || ""} onChange={(event) => onChange({ ...form, internal_notes: event.target.value })} /></label>
  </div><div className="mt-5 flex justify-end gap-2"><Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={saving || !form.name.trim()} type="submit">{saving ? "Guardando..." : "Guardar"}</Button></div></form></div>;
}

function SessionDetail({ eventId, item, responsible, canManage, staff, role, onClose, onTransition }: { eventId: string; item: EventSession; responsible?: string; canManage: boolean; staff: EventStaff[]; role?: UserRole | null; onClose: () => void; onTransition: (status: EventSessionStatus) => void }) {
  return <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-slate-950/45 p-4"><div className="my-6 w-full max-w-4xl rounded-lg bg-white p-5 shadow-2xl"><div className="flex items-start justify-between gap-3"><div><h3 className="text-xl font-bold">{item.name}</h3><p className="text-sm text-slate-600">{statusLabels[item.status]}</p></div><Button variant="secondary" onClick={onClose}>Cerrar</Button></div><dl className="mt-5 grid gap-3 text-sm md:grid-cols-2"><div><dt className="font-semibold">Fecha y horario</dt><dd>{item.session_date || "Sin fecha"} {item.start_time?.slice(0, 5) || ""} {item.end_time ? `– ${item.end_time.slice(0, 5)}` : ""}</dd></div><div><dt className="font-semibold">Recinto / escenario</dt><dd>{[item.venue_name, item.stage_name].filter(Boolean).join(" · ") || "Sin definir"}</dd></div><div><dt className="font-semibold">Asistentes</dt><dd>{item.real_attendees ?? "—"} reales / {item.expected_attendees} esperados</dd></div><div><dt className="font-semibold">Responsable</dt><dd>{responsible || "Sin responsable"}</dd></div>{item.description ? <div className="md:col-span-2"><dt className="font-semibold">Descripción</dt><dd>{item.description}</dd></div> : null}{item.internal_notes && role !== "CLIENT" ? <div className="md:col-span-2"><dt className="font-semibold">Notas internas</dt><dd>{item.internal_notes}</dd></div> : null}</dl>{canManage && transitions[item.status].length ? <div className="mt-5 border-t pt-4"><p className="mb-2 text-sm font-semibold">Cambiar estado</p><div className="flex flex-wrap gap-2">{transitions[item.status].map((status) => <Button key={status} variant="secondary" onClick={() => onTransition(status)}>{statusLabels[status]}</Button>)}</div></div> : null}<ShowOperationsPanel eventId={eventId} role={role} session={item} staff={staff} /></div></div>;
}
