"use client";

import Link from "next/link";
import { Plus } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { ModalShell } from "@/components/common/ModalShell";
import { useToast } from "@/components/common/ToastProvider";
import { LogbookDialog } from "@/components/logbooks/LogbookDialog";
import { Button } from "@/components/ui/button";
import {
  cancelLogbookInstance, createEventLogbook, getEventLogbooks, getLogbookInstance,
  getLogbookTemplate, getLogbookTemplates, openLogbookInstance,
} from "@/lib/api/logbooks";
import { getEventStaff } from "@/lib/api/staff";
import { getEventZones } from "@/lib/api/zones";
import { logbookError } from "@/lib/logbook-errors";
import { logbookLabel, logbookModeLabels, logbookStageLabels, logbookStatusLabels } from "@/lib/logbook-labels";
import type { EventStaff } from "@/types/staff";
import type { LogbookInstance, LogbookInstanceDetail, LogbookTemplateDetail } from "@/types/logbook";
import type { Zone } from "@/types/zone";

export function EventLogbooksTab({ eventId, role }: { eventId: string; role?: string | null }) {
  const [items, setItems] = useState<Array<LogbookInstance & { detail?: LogbookInstanceDetail }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("ALL");
  const [templateFilter, setTemplateFilter] = useState("ALL");
  const [stageFilter, setStageFilter] = useState("ALL");

  async function load() {
    setLoading(true); setError("");
    try {
      const list = await getEventLogbooks(eventId);
      setItems(await Promise.all(list.items.map(async (item) => {
        try { return { ...item, detail: await getLogbookInstance(item.id) }; }
        catch { return item; }
      })));
    } catch (reason) {
      setError(logbookError(reason, "No se pudieron cargar las bitácoras."));
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [eventId]);
  const shown = items.filter((item) =>
    (filter === "ALL" || item.status === filter)
    && (templateFilter === "ALL" || item.template_id === templateFilter)
    && (stageFilter === "ALL" || item.operational_stage === stageFilter));

  return <div className="space-y-4">
    <div className="flex flex-wrap justify-between gap-3">
      <select className="rounded-xl border p-2" onChange={(event) => setFilter(event.target.value)} value={filter}><option value="ALL">Todos los estados</option>{["SCHEDULED","OPEN","IN_PROGRESS","UNDER_REVIEW","CHANGES_REQUESTED","COMPLETED","CANCELLED"].map((value) => <option key={value} value={value}>{logbookLabel(logbookStatusLabels,value)}</option>)}</select>
      <select className="rounded-xl border p-2" onChange={(event) => setTemplateFilter(event.target.value)} value={templateFilter}><option value="ALL">Todas las plantillas</option>{Array.from(new Map(items.map((item) => [item.template_id,item.name])).entries()).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select>
      <select className="rounded-xl border p-2" onChange={(event) => setStageFilter(event.target.value)} value={stageFilter}><option value="ALL">Todas las etapas</option>{Object.entries(logbookStageLabels).map(([value,label]) => <option key={value} value={value}>{label}</option>)}</select>
      {role !== "CLIENT" ? <Button onClick={() => setOpen(true)}><Plus className="mr-1 h-4 w-4"/>Asignar bitácora</Button> : null}
    </div>
    {loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={load}/> : shown.length === 0 ? <EmptyState title="Sin bitácoras" description="Aún no hay ejecuciones para este evento."/> : <div className="grid gap-3">{shown.map((item) => <article className="rounded-xl border bg-white p-4" key={item.id}>
      <div className="flex flex-wrap items-start justify-between gap-2"><div><Link className="font-semibold hover:text-emerald-700" href={role === "ADMIN" || role === "SUPER_ADMIN" ? `/admin/bitacoras/ejecuciones/${item.id}` : `/supervisor/bitacoras/${item.id}`}>{item.name}</Link><p className="text-xs text-slate-500">{logbookLabel(logbookStageLabels,item.operational_stage)} · {logbookLabel(logbookModeLabels,item.assignment_mode)} · {logbookLabel(logbookStatusLabels,item.status)}</p></div><div className="flex flex-wrap gap-2"><Link className="inline-flex h-9 items-center justify-center rounded-xl bg-emerald-700 px-3 text-sm font-medium text-white hover:bg-emerald-800" href={role === "ADMIN" || role === "SUPER_ADMIN" ? `/admin/bitacoras/ejecuciones/${item.id}` : `/supervisor/bitacoras/${item.id}`}>{role === "ADMIN" || role === "SUPER_ADMIN" ? "Administrar bitácora" : "Revisar bitácora"}</Link><InstanceActions item={item} done={load}/></div></div>
      {item.detail ? <div className="mt-3 grid grid-cols-3 gap-2 text-center text-sm"><Metric label="Cumplimiento" value={item.detail.metrics.completion_percentage}/><Metric label="Participación" value={item.detail.metrics.participation_percentage}/><Metric label="Aprobación" value={item.detail.metrics.approval_percentage}/></div> : null}
      <p className="mt-3 text-xs text-slate-500">Apertura: {item.opens_at ? new Date(item.opens_at).toLocaleString("es-CL") : "Inmediata"} · Vence: {item.due_at ? new Date(item.due_at).toLocaleString("es-CL") : "Sin vencimiento"}</p>
    </article>)}</div>}
    {open ? <AssignLogbook eventId={eventId} close={() => setOpen(false)} done={() => { setOpen(false); void load(); }}/> : null}
  </div>;
}

function InstanceActions({ item, done }: { item: LogbookInstance; done: () => Promise<void> }) {
  const { toast } = useToast();
  const [action, setAction] = useState<"open"|"cancel"|null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function confirmAction() {
    if (busy) return;
    setBusy(true); setError("");
    try {
      if (action === "open") { await openLogbookInstance(item.id); toast({ title: "Ejecución abierta", tone: "success" }); }
      else if (action === "cancel") { await cancelLogbookInstance(item.id,reason.trim()); toast({ title: "Ejecución cancelada",description:"La información histórica se conserva.",tone:"success" }); }
      await done(); setAction(null); setReason("");
    } catch (cause) { setError(logbookError(cause)); }
    finally { setBusy(false); }
  }
  return <>{item.status === "SCHEDULED" ? <Button onClick={() => { setError(""); setAction("open"); }} size="sm">Abrir</Button> : null}{!["COMPLETED","CANCELLED"].includes(item.status) ? <Button onClick={() => { setError("");setAction("cancel"); }} size="sm" variant="secondary">Cancelar</Button> : null}
    <LogbookDialog busy={busy} confirmLabel="Abrir ejecución" description={`La bitácora quedará disponible en modalidad ${logbookLabel(logbookModeLabels,item.assignment_mode)}.`} error={error} onClose={() => setAction(null)} onConfirm={() => void confirmAction()} open={action === "open"} title="Abrir ejecución"/>
    <LogbookDialog busy={busy} confirmDisabled={!reason.trim()} confirmLabel="Cancelar ejecución" description="Los participantes ya no podrán continuar y la información histórica se conservará." error={error} onClose={() => setAction(null)} onConfirm={() => void confirmAction()} open={action === "cancel"} title="Cancelar ejecución" tone="danger"><label className="grid gap-1 text-sm font-medium">Motivo obligatorio<textarea className="min-h-24 rounded-xl border p-3" maxLength={500} onChange={(event) => setReason(event.target.value)} value={reason}/></label></LogbookDialog>
  </>;
}

function AssignLogbook({ eventId, close, done }: { eventId: string; close: () => void; done: () => void }) {
  const { toast } = useToast();
  const [templates, setTemplates] = useState<LogbookTemplateDetail[]>([]);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [versionId, setVersionId] = useState("");
  const [participants, setParticipants] = useState<string[]>([]);
  const [mode, setMode] = useState<"INDIVIDUAL"|"SHARED">("INDIVIDUAL");
  const [supervisor, setSupervisor] = useState("");
  const [zone, setZone] = useState("");
  const [opens, setOpens] = useState("");
  const [due, setDue] = useState("");
  const [clientVisible, setClientVisible] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const requestInFlight = useRef(false);

  useEffect(() => {
    Promise.all([getLogbookTemplates(),getEventStaff(eventId),getEventZones(eventId)]).then(async ([list,members,eventZones]) => {
      const details = await Promise.all(list.items.filter((item) => item.status === "ACTIVE").map((item) => getLogbookTemplate(item.id)));
      setTemplates(details); setStaff(members); setZones(eventZones);
      setVersionId(details.flatMap((item) => item.versions).find((version) => version.status === "PUBLISHED")?.id || "");
    }).catch((cause) => setError(logbookError(cause, "No se pudieron cargar los datos para asignar la bitácora.")));
  }, [eventId]);

  const published = useMemo(() => templates.flatMap((template) => template.versions.filter((version) => version.status === "PUBLISHED").map((version) => ({ ...version,name:template.name }))), [templates]);
  const selectedVersion = published.find((version) => version.id === versionId);
  const participantNames = participants.map((id) => staff.find((member) => member.user_id === id)?.user?.full_name || id);
  const supervisorName = staff.find((member) => member.user_id === supervisor)?.user?.full_name || "Sin supervisor";
  const zoneName = zones.find((item) => item.id === zone)?.name || "Todo el evento";
  const invalidDates = Boolean(opens && due && new Date(due) <= new Date(opens));
  const canReview = Boolean(versionId && participants.length && !invalidDates);

  async function submit() {
    if (saving || requestInFlight.current || !canReview) return;
    requestInFlight.current = true; setSaving(true); setError("");
    try {
      await createEventLogbook(eventId,{ template_version_id:versionId,assignment_mode:mode,participant_ids:participants,supervisor_id:supervisor || null,zone_id:zone || null,opens_at:opens ? new Date(opens).toISOString() : null,due_at:due ? new Date(due).toISOString() : null,client_visibility:clientVisible });
      toast({ title: "Bitácora asignada", tone: "success" });
      setReviewing(false); done();
    } catch (cause) { setError(logbookError(cause, "No se pudo asignar la bitácora.")); }
    finally { requestInFlight.current = false; setSaving(false); }
  }

  return <ModalShell title="Asignar bitácora" description="Configura la ejecución y revisa el resumen antes de confirmarla." onClose={() => { if (!saving) close(); }}>
    <div className="max-h-[75vh] space-y-4 overflow-y-auto">
      <label className="grid gap-1 text-sm">Plantilla publicada<select disabled={saving} className="rounded-xl border p-3" onChange={(event) => setVersionId(event.target.value)} value={versionId}>{published.map((version) => <option key={version.id} value={version.id}>{version.name} · v{version.version_number}</option>)}</select></label>
      <label className="grid gap-1 text-sm">Modalidad<select disabled={saving} className="rounded-xl border p-3" onChange={(event) => setMode(event.target.value as "INDIVIDUAL"|"SHARED")} value={mode}><option value="INDIVIDUAL">Individual</option><option value="SHARED">Compartida</option></select></label>
      <fieldset disabled={saving} className="rounded-xl border p-3"><legend className="text-sm font-medium">Participantes</legend>{staff.filter((member) => !["CLIENT","ADMIN","SUPER_ADMIN"].includes(member.user?.role || "")).map((member) => <label className="mt-2 flex gap-2 text-sm" key={member.user_id}><input checked={participants.includes(member.user_id)} onChange={(event) => setParticipants((current) => event.target.checked ? [...current,member.user_id] : current.filter((id) => id !== member.user_id))} type="checkbox"/>{member.user?.full_name || member.user_id}</label>)}</fieldset>
      <label className="grid gap-1 text-sm">Supervisor<select disabled={saving} className="rounded-xl border p-3" onChange={(event) => setSupervisor(event.target.value)} value={supervisor}><option value="">Sin supervisor</option>{staff.filter((member) => member.user?.role === "SUPERVISOR").map((member) => <option key={member.user_id} value={member.user_id}>{member.user?.full_name}</option>)}</select></label>
      <label className="grid gap-1 text-sm">Zona<select disabled={saving} className="rounded-xl border p-3" onChange={(event) => setZone(event.target.value)} value={zone}><option value="">Todo el evento</option>{zones.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2"><label className="text-sm">Apertura<input disabled={saving} className="mt-1 w-full rounded-xl border p-3" onChange={(event) => setOpens(event.target.value)} type="datetime-local" value={opens}/></label><label className="text-sm">Vencimiento<input disabled={saving} className="mt-1 w-full rounded-xl border p-3" onChange={(event) => setDue(event.target.value)} type="datetime-local" value={due}/></label></div>
      {invalidDates ? <p className="text-sm text-red-600">La fecha de vencimiento debe ser posterior a la apertura.</p> : null}
      <label className="flex gap-2 text-sm"><input checked={clientVisible} disabled={saving} onChange={(event) => setClientVisible(event.target.checked)} type="checkbox"/>Visible en el portal del cliente</label>
      {error && !reviewing ? <p className="text-sm text-red-600">{error}</p> : null}
      <div className="flex justify-end gap-2"><Button disabled={saving} onClick={close} variant="secondary">Cancelar</Button><Button disabled={saving || !canReview} onClick={() => { setError(""); setReviewing(true); }}>Revisar asignación</Button></div>
    </div>
    <LogbookDialog busy={saving} cancelLabel="Volver y editar" confirmDisabled={!canReview} confirmLabel="Confirmar asignación" description={mode === "SHARED" ? "Los participantes colaborarán sobre una única ejecución compartida." : `Se generará una entrega independiente para cada uno de los ${participants.length} participantes.`} error={error} onClose={() => { if (!saving) setReviewing(false); }} onConfirm={() => void submit()} open={reviewing} title="Revisar asignación">
      <dl className="grid gap-2 rounded-xl bg-slate-50 p-4 text-sm">
        <Summary label="Plantilla" value={selectedVersion?.name || "Sin seleccionar"}/>
        <Summary label="Versión" value={selectedVersion ? `v${selectedVersion.version_number}` : "Sin seleccionar"}/>
        <Summary label="Evento" value={eventId}/>
        <Summary label="Modalidad" value={logbookLabel(logbookModeLabels,mode)}/>
        <Summary label="Supervisor" value={supervisorName}/>
        <Summary label="Participantes" value={`${participants.length}: ${participantNames.join(", ")}`}/>
        <Summary label="Zona" value={zoneName}/>
        <Summary label="Apertura" value={opens ? new Date(opens).toLocaleString("es-CL") : "Inmediata"}/>
        <Summary label="Vencimiento" value={due ? new Date(due).toLocaleString("es-CL") : "Sin vencimiento"}/>
        <Summary label="Visibilidad cliente" value={clientVisible ? "Visible" : "No visible"}/>
      </dl>
      <p className="mt-3 text-sm text-slate-600">Al confirmar se creará la ejecución y se notificará la actualización en la lista del evento.</p>
    </LogbookDialog>
  </ModalShell>;
}

function Summary({ label, value }: { label: string; value: string }) { return <div className="grid grid-cols-[8rem_1fr] gap-2"><dt className="font-medium">{label}</dt><dd className="break-words">{value}</dd></div>; }
function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-slate-50 p-2"><strong>{value}%</strong><p className="text-xs text-slate-500">{label}</p></div>; }
