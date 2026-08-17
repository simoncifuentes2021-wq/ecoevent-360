"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Plus, Trash2 } from "lucide-react";

import { ConfirmDialog } from "@/components/common/ConfirmDialog";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getEventEvidences } from "@/lib/api/evidences";
import { getEventIncidents } from "@/lib/api/incidents";
import { assignShowStaff, getShowOperationalSummary, getShowStaff, removeShowStaff } from "@/lib/api/showOperations";
import { getEventTasks } from "@/lib/api/tasks";
import type { EventSession } from "@/types/eventSession";
import type { UserRole } from "@/types/roles";
import type { ShowOperationalSummary, ShowStaffAssignment, ShowStaffInput } from "@/types/showOperations";
import type { EventStaff } from "@/types/staff";

const tabs = ["Resumen", "Personal y turnos", "Tareas", "Incidencias", "Evidencias"] as const;

export function ShowOperationsPanel({ eventId, session, staff, role }: { eventId: string; session: EventSession; staff: EventStaff[]; role?: UserRole | null }) {
  const { toast } = useToast();
  const [active, setActive] = useState<(typeof tabs)[number]>("Resumen");
  const [summary, setSummary] = useState<ShowOperationalSummary | null>(null);
  const [assignments, setAssignments] = useState<ShowStaffAssignment[]>([]);
  const [tasks, setTasks] = useState<{ id: string; title: string; status: string }[]>([]);
  const [incidents, setIncidents] = useState<{ id: string; title: string; status: string }[]>([]);
  const [evidences, setEvidences] = useState<{ id: string; description?: string | null; file_type: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [editor, setEditor] = useState(false);
  const [removing, setRemoving] = useState<ShowStaffAssignment | null>(null);
  const [form, setForm] = useState<ShowStaffInput>({ event_staff_id: "", shift_start: null, shift_end: null, operational_role: "", notes: "" });
  const canManage = role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (role === "LOGISTICS_OPERATOR") {
        setSummary(await getShowOperationalSummary(session.id));
        setAssignments((await getShowStaff(session.id)).items);
        setTasks([]); setIncidents([]); setEvidences([]);
        return;
      }
      const [summaryData, taskData, incidentData, evidenceData] = await Promise.all([
        getShowOperationalSummary(session.id), getEventTasks(eventId, { session_id: session.id }),
        getEventIncidents(eventId, { session_id: session.id }), getEventEvidences(eventId, { session_id: session.id })
      ]);
      setSummary(summaryData); setTasks(taskData.items); setIncidents(incidentData.items); setEvidences(evidenceData.items);
      if (role !== "CLIENT") setAssignments((await getShowStaff(session.id)).items);
    } catch (cause) {
      toast({ tone: "error", title: "No se pudo cargar la operación del show", description: cause instanceof Error ? cause.message : undefined });
    } finally { setLoading(false); }
  }, [eventId, role, session.id, toast]);

  useEffect(() => { void load(); }, [load]);

  async function saveAssignment() {
    try {
      await assignShowStaff(session.id, { ...form, shift_start: form.shift_start || null, shift_end: form.shift_end || null, operational_role: form.operational_role?.trim() || null, notes: form.notes?.trim() || null });
      setEditor(false); setForm({ event_staff_id: "", shift_start: null, shift_end: null, operational_role: "", notes: "" });
      toast({ tone: "success", title: "Personal asignado al show" }); await load();
    } catch (cause) { toast({ tone: "error", title: "No se pudo asignar", description: cause instanceof Error ? cause.message : undefined }); }
  }

  async function confirmRemove() {
    if (!removing) return;
    await removeShowStaff(removing.id); setRemoving(null); await load();
    toast({ tone: "success", title: "Asignación retirada" });
  }

  if (loading) return <LoadingState label="Cargando operación del show..." />;
  return <section className="mt-5 border-t pt-4">
    <div className="flex gap-2 overflow-x-auto pb-2">{tabs.filter((tab) => role !== "LOGISTICS_OPERATOR" || tab === "Resumen" || tab === "Personal y turnos").map((tab) => <button className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold ${active === tab ? "bg-emerald-700 text-white" : "bg-slate-100"}`} key={tab} type="button" onClick={() => setActive(tab)}>{tab}</button>)}</div>
    {active === "Resumen" && summary ? <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-5">{[["Personal", summary.staff_count], ["Turnos", summary.active_shift_count], ["Tareas", Object.values(summary.tasks_by_status).reduce((a, b) => a + (b || 0), 0)], ["Incidencias", Object.values(summary.incidents_by_status).reduce((a, b) => a + (b || 0), 0)], ["Evidencias", summary.evidence_count]].map(([label, value]) => <div className="rounded-lg bg-slate-50 p-3" key={label}><p className="text-xs text-slate-500">{label}</p><p className="text-xl font-bold">{value}</p></div>)}</div> : null}
    {active === "Personal y turnos" ? <div className="mt-3 space-y-2"><div className="flex justify-end">{canManage ? <Button type="button" onClick={() => setEditor(true)}><Plus className="h-4 w-4" />Asignar personal</Button> : null}</div>{assignments.map((item) => <div className="flex items-start justify-between rounded-lg border p-3" key={item.id}><div><p className="font-semibold">{item.user?.full_name || "Personal del evento"}</p><p className="text-xs text-slate-500">{item.operational_role || "Sin función"} · {item.shift_start ? new Date(item.shift_start).toLocaleString("es-CL", { timeZone: "America/Santiago" }) : "Sin inicio"} – {item.shift_end ? new Date(item.shift_end).toLocaleString("es-CL", { timeZone: "America/Santiago" }) : "Sin término"}</p>{item.overlap_warning ? <p className="mt-1 flex gap-1 text-xs text-amber-700"><AlertTriangle className="h-4 w-4" />Turno superpuesto</p> : null}</div>{canManage ? <Button variant="secondary" type="button" onClick={() => setRemoving(item)}><Trash2 className="h-4 w-4" /></Button> : null}</div>)}{!assignments.length ? <p className="text-sm text-slate-500">Sin personal específico; el personal general del evento se conserva.</p> : null}</div> : null}
    {active === "Tareas" ? <OperationList items={tasks} empty="No hay tareas asociadas a este show." /> : null}
    {active === "Incidencias" ? <OperationList items={incidents} empty="No hay incidencias asociadas a este show." /> : null}
    {active === "Evidencias" ? <OperationList items={evidences.map((item) => ({ ...item, title: item.description || item.file_type, status: item.file_type }))} empty="No hay evidencias relacionadas con este show." /> : null}
    {editor ? <div className="fixed inset-0 z-[60] grid place-items-center bg-slate-950/45 p-4"><form className="w-full max-w-lg rounded-lg bg-white p-5" onSubmit={(event) => { event.preventDefault(); void saveAssignment(); }}><h3 className="text-lg font-bold">Asignar personal al show</h3><div className="mt-4 grid gap-3"><label className="grid gap-1 text-sm font-semibold">Personal<select required className="h-10 rounded-md border px-3" value={form.event_staff_id} onChange={(event) => setForm({ ...form, event_staff_id: event.target.value })}><option value="">Seleccionar</option>{staff.map((item) => <option key={item.id} value={item.id}>{item.user?.full_name || item.user_id}</option>)}</select></label><label className="grid gap-1 text-sm font-semibold">Función<Input value={form.operational_role || ""} onChange={(event) => setForm({ ...form, operational_role: event.target.value })} /></label><div className="grid grid-cols-2 gap-3"><label className="grid gap-1 text-sm font-semibold">Inicio<Input type="datetime-local" value={form.shift_start || ""} onChange={(event) => setForm({ ...form, shift_start: event.target.value || null })} /></label><label className="grid gap-1 text-sm font-semibold">Término<Input type="datetime-local" value={form.shift_end || ""} onChange={(event) => setForm({ ...form, shift_end: event.target.value || null })} /></label></div><label className="grid gap-1 text-sm font-semibold">Notas internas<textarea className="min-h-20 rounded-md border p-3" value={form.notes || ""} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label></div><div className="mt-4 flex justify-end gap-2"><Button variant="secondary" type="button" onClick={() => setEditor(false)}>Cancelar</Button><Button disabled={!form.event_staff_id} type="submit">Asignar</Button></div></form></div> : null}
    <ConfirmDialog open={Boolean(removing)} title="Retirar asignación" description="La persona seguirá perteneciendo al personal general del evento." confirmLabel="Retirar" onClose={() => setRemoving(null)} onConfirm={() => void confirmRemove()} />
  </section>;
}

function OperationList({ items, empty }: { items: { id: string; title: string; status: string }[]; empty: string }) {
  return <div className="mt-3 space-y-2">{items.map((item) => <div className="flex justify-between rounded-lg border p-3 text-sm" key={item.id}><span className="font-semibold">{item.title}</span><span className="text-slate-500">{item.status}</span></div>)}{!items.length ? <p className="text-sm text-slate-500">{empty}</p> : null}</div>;
}
