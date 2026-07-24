"use client";

import { useEffect, useMemo, useState } from "react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { LogbookDialog } from "@/components/logbooks/LogbookDialog";
import { LogbookEvidencePreview } from "@/components/logbooks/LogbookEvidencePreview";
import { Button } from "@/components/ui/button";
import {
  addLogbookParticipants,
  approveLogbook,
  createCorrectiveTask,
  createLogbookIncident,
  getLogbookInstance,
  removeLogbookParticipant,
  requestLogbookChanges,
} from "@/lib/api/logbooks";
import { getEventStaff } from "@/lib/api/staff";
import { logbookError } from "@/lib/logbook-errors";
import { validateLogbook } from "@/lib/logbook-validation";
import { logbookLabel, logbookModeLabels, logbookStageLabels, logbookStatusLabels } from "@/lib/logbook-labels";
import type { EventStaff } from "@/types/staff";
import type { LogbookEvidence, LogbookInstanceDetail, LogbookItem, LogbookResponse } from "@/types/logbook";

type Assignment = LogbookInstanceDetail["assignments"][number];
type MainDialog = "add" | "remove" | "approve" | "changes" | null;

export function SupervisorLogbookDetail({ id }: { id: string }) {
  const { toast } = useToast();
  const [data, setData] = useState<LogbookInstanceDetail | null>(null);
  const [staff, setStaff] = useState<EventStaff[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [selected, setSelected] = useState<string | null>(null);
  const [dialog, setDialog] = useState<MainDialog>(null);
  const [participantIds, setParticipantIds] = useState<string[]>([]);
  const [removeTarget, setRemoveTarget] = useState<Assignment | null>(null);
  const [comment, setComment] = useState("");
  const [pageError, setPageError] = useState("");
  const [dialogError, setDialogError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setPageError("");
    try {
      const detail = await getLogbookInstance(id);
      setData(detail);
      setStaff(await getEventStaff(detail.event_id));
      setSelected((value) => value || detail.assignments[0]?.id || null);
    } catch (reason) {
      setPageError(logbookError(reason, "No se pudo cargar la bitácora."));
    }
  }

  useEffect(() => { void load(); }, [id]);
  const assignments = useMemo(
    () => filter === "ALL" ? data?.assignments || [] : (data?.assignments || []).filter((item) => item.status === filter),
    [data, filter],
  );

  if (pageError) return <ErrorState message={pageError} onRetry={load} />;
  if (!data) return <LoadingState />;
  const assignment = data.assignments.find((item) => item.id === selected) || assignments[0];
  const reviewResponses = new Map(
    (data.assignment_mode === "SHARED"
      ? data.assignments.flatMap((item) => item.responses)
      : assignment?.responses || []
    ).map((response) => [response.logbook_item_id, response]),
  );
  const reviewSummary = validateLogbook(data.version.sections, reviewResponses);
  const canApprove = Boolean(
    assignment
    && ["SUBMITTED", "RESUBMITTED"].includes(assignment.status)
    && reviewSummary.complete,
  );
  const available = staff.filter((member) =>
    !data.assignments.some((item) => item.user_id === member.user_id)
    && !["CLIENT", "ADMIN", "SUPER_ADMIN"].includes(member.user?.role || ""),
  );

  function openDialog(next: MainDialog) {
    setDialogError("");
    setComment("");
    setParticipantIds([]);
    setDialog(next);
  }

  async function run(action: () => Promise<unknown>, success: string) {
    if (busy) return false;
    setBusy(true); setDialogError("");
    try {
      await action();
      await load();
      setDialog(null);
      toast({ title: success, tone: "success" });
      return true;
    } catch (reason) {
      setDialogError(logbookError(reason));
      return false;
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border bg-white p-5">
        <h1 className="text-2xl font-bold">{data.name}</h1>
        <p className="text-sm text-slate-500">
          {data.event_name} · {logbookLabel(logbookStageLabels, data.operational_stage)} · Versión {data.version.version_number} · {logbookLabel(logbookModeLabels, data.assignment_mode)} · {logbookLabel(logbookStatusLabels, data.status)}
        </p>
        <div className="mt-4 grid grid-cols-3 gap-2">
          <Metric label="Cumplimiento" value={data.metrics.completion_percentage} />
          <Metric label="Participación" value={data.metrics.participation_percentage} />
          <Metric label="Aprobación" value={data.metrics.approval_percentage} />
        </div>
        <Button className="mt-3" disabled={busy || available.length === 0} onClick={() => openDialog("add")} size="sm" variant="secondary">
          Agregar participante
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[18rem_1fr]">
        <aside className="rounded-2xl border bg-white p-3">
          <select className="mb-3 w-full rounded-lg border p-2" onChange={(event) => setFilter(event.target.value)} value={filter}>
            <option value="ALL">Todos</option>
            {["PENDING", "IN_PROGRESS", "SUBMITTED", "RESUBMITTED", "CHANGES_REQUESTED", "APPROVED"].map((status) => <option key={status} value={status}>{logbookLabel(logbookStatusLabels, status)}</option>)}
          </select>
          {assignments.map((item) => (
            <div key={item.id}>
              <button className={`mb-2 w-full rounded-xl p-3 text-left text-sm ${item.id === assignment?.id ? "bg-emerald-700 text-white" : "bg-slate-50"}`} onClick={() => setSelected(item.id)}>
                <strong>{item.user_name || item.user_id}</strong><br />
                <span>{logbookLabel(logbookStatusLabels, item.status)} · intento {item.attempt_number}</span>
              </button>
              {item.status !== "CANCELLED" ? (
                <Button className="mb-2 w-full" disabled={busy} onClick={() => { setRemoveTarget(item); openDialog("remove"); }} size="sm" variant="ghost">
                  Retirar participante
                </Button>
              ) : null}
            </div>
          ))}
        </aside>

        {assignment ? (
          <main className="space-y-4">
            <div className="flex flex-wrap justify-between gap-2 rounded-xl border bg-white p-4">
              <div>
                <h2 className="font-semibold">{assignment.user_name || "Entrega compartida"}</h2>
                <p className="text-sm text-slate-500">{logbookLabel(logbookStatusLabels, assignment.status)} · intento {assignment.attempt_number}</p>
              </div>
              {["SUBMITTED", "RESUBMITTED"].includes(assignment.status) ? (
                <div className="flex gap-2">
                  <Button disabled={busy} onClick={() => openDialog("approve")}>Aprobar</Button>
                  <Button disabled={busy} onClick={() => openDialog("changes")} variant="secondary">Solicitar cambios</Button>
                </div>
              ) : null}
            </div>
            {data.version.sections.map((section) => (
              <section className="rounded-2xl border bg-white p-4" key={section.id}>
                <h3 className="font-semibold">{section.title}</h3>
                {section.items.map((item) => (
                  <ResponseCard
                    assignment={assignment}
                    busy={busy}
                    item={item}
                    key={item.id}
                    onDone={load}
                    response={assignment.responses.find((response) => response.logbook_item_id === item.id)}
                    staff={staff}
                  />
                ))}
              </section>
            ))}
            {assignment.history.length ? <History assignment={assignment} /> : null}
          </main>
        ) : <div className="rounded-xl border bg-white p-6">No hay entregas para el filtro.</div>}
      </div>

      <LogbookDialog
        busy={busy}
        confirmDisabled={participantIds.length === 0}
        confirmLabel="Agregar participantes"
        description={`Se agregarán ${participantIds.length} participantes a “${data.event_name}” en modalidad ${logbookLabel(logbookModeLabels, data.assignment_mode)}.`}
        error={dialogError}
        onClose={() => setDialog(null)}
        onConfirm={() => void run(() => addLogbookParticipants(id, participantIds), "Participantes agregados")}
        open={dialog === "add"}
        title="Agregar participantes"
      >
        <fieldset className="space-y-2"><legend className="text-sm font-semibold">Selecciona el equipo</legend>
          {available.map((member) => <label className="flex min-h-11 items-center gap-2 rounded-xl border p-3 text-sm" key={member.user_id}><input checked={participantIds.includes(member.user_id)} onChange={(event) => setParticipantIds((current) => event.target.checked ? [...current, member.user_id] : current.filter((value) => value !== member.user_id))} type="checkbox" />{member.user?.full_name || member.user_id}</label>)}
        </fieldset>
      </LogbookDialog>

      <LogbookDialog
        busy={busy}
        confirmLabel="Retirar participante"
        description={`${removeTarget?.user_name || "El participante"} dejará de colaborar. ${removeTarget?.responses.length ? "Sus respuestas y autoría se conservarán en el historial." : "Todavía no tiene respuestas registradas."}`}
        error={dialogError}
        onClose={() => setDialog(null)}
        onConfirm={() => removeTarget && void run(() => removeLogbookParticipant(id, removeTarget.id), "Participante retirado")}
        open={dialog === "remove"}
        title="Retirar participante"
        tone="warning"
      />

      <LogbookDialog
        busy={busy}
        confirmDisabled={!canApprove}
        confirmLabel="Aprobar bitácora"
        description={data.assignment_mode === "SHARED"
          ? `Aprobarás la ejecución compartida “${data.name}”. La acción afectará a todos sus participantes, intento ${assignment?.attempt_number || 0}.`
          : `Aprobarás únicamente la entrega de ${assignment?.user_name || "este participante"} para “${data.event_name}”, intento ${assignment?.attempt_number || 0}.`}
        error={dialogError}
        onClose={() => setDialog(null)}
        onConfirm={() => assignment && void run(() => approveLogbook(assignment.id), "Bitácora aprobada")}
        open={dialog === "approve"}
        title="Aprobar bitácora"
      >
        <div className="grid grid-cols-2 gap-2 text-sm">
          <Count label="Total de ítems" value={reviewSummary.totalItems}/>
          <Count label="Respondidos" value={reviewSummary.answeredItems}/>
          <Count label="Incumplimientos" value={reviewSummary.failedItems}/>
          <Count label="Evidencias" value={reviewSummary.evidenceCount}/>
        </div>
        <p className="mt-3 text-sm"><strong>Estado:</strong> {logbookLabel(logbookStatusLabels, assignment?.status || "PENDING")}</p>
        {!reviewSummary.complete ? <ApprovalRequirements summary={reviewSummary}/> : <p className="mt-3 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">La entrega cumple los requisitos conocidos para aprobación.</p>}
      </LogbookDialog>

      <LogbookDialog
        busy={busy}
        confirmDisabled={!comment.trim()}
        confirmLabel="Solicitar correcciones"
        description={`La bitácora volverá a quedar editable y el comentario será visible para los participantes.${data.assignment_mode === "SHARED" ? " En modalidad compartida afecta a toda la ejecución." : ""}`}
        error={dialogError}
        onClose={() => setDialog(null)}
        onConfirm={() => assignment && void run(() => requestLogbookChanges(assignment.id, comment.trim()), "Correcciones solicitadas")}
        open={dialog === "changes"}
        title="Solicitar correcciones"
        tone="warning"
      >
        <label className="grid gap-1 text-sm font-medium">Comentario obligatorio<textarea autoFocus className="min-h-28 rounded-xl border p-3" maxLength={1000} onChange={(event) => setComment(event.target.value)} value={comment}/><span className="text-xs text-slate-500">{comment.length}/1000 caracteres</span></label>
      </LogbookDialog>
    </div>
  );
}

function ResponseCard({ assignment, item, response, busy, staff, onDone }: { assignment: Assignment; item: LogbookItem; response?: LogbookResponse; busy: boolean; staff: EventStaff[]; onDone: () => Promise<void> }) {
  const { toast } = useToast();
  const [kind, setKind] = useState<"incident" | "task" | null>(null);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("MEDIUM");
  const [assignee, setAssignee] = useState(assignment.user_id);
  const [scheduled, setScheduled] = useState("");
  const [evidenceIds, setEvidenceIds] = useState<string[]>([]);
  const [previewEvidence, setPreviewEvidence] = useState<LogbookEvidence | null>(null);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState("");
  const value = response?.is_not_applicable ? "No aplica" : response?.text_value ?? response?.numeric_value ?? response?.boolean_value ?? response?.selected_option_id ?? "Sin respuesta";
  const evidences = response?.evidences.filter((evidence) => !evidence.deleted_at) || [];

  function open(next: "incident" | "task") {
    setKind(next); setError(""); setTitle(next === "incident" ? `Hallazgo: ${item.title}` : `Corregir: ${item.title}`);
    setPriority("MEDIUM"); setAssignee(assignment.user_id); setScheduled(""); setEvidenceIds(evidences.map((evidence) => evidence.id));
  }

  async function create() {
    if (!response || processing) return;
    setProcessing(true); setError("");
    try {
      if (kind === "incident") await createLogbookIncident(response.id, { title, description: response.comment || item.description, incident_type: "OTHER", priority, evidence_ids: evidenceIds });
      if (kind === "task") await createCorrectiveTask(response.id, { title, description: response.comment || item.description, assigned_to: assignee, scheduled_at: scheduled ? new Date(scheduled).toISOString() : null, priority, evidence_ids: evidenceIds });
      await onDone(); setKind(null);
      toast({ title: kind === "incident" ? "Incidencia creada" : "Tarea correctiva creada", tone: "success" });
    } catch (reason) { setError(logbookError(reason)); }
    finally { setProcessing(false); }
  }

  return <article className="mt-3 border-t pt-3">
    <div className="flex flex-wrap justify-between gap-2"><div><p className="font-medium">{item.title}</p><p className="text-sm">{String(value)} · <span className={response?.result_status === "FAILED" ? "text-red-600" : "text-emerald-700"}>{logbookLabel(logbookStatusLabels, response?.result_status || "PENDING")}</span></p>{response?.comment ? <p className="mt-1 rounded bg-amber-50 p-2 text-sm">{response.comment}</p> : null}{response?.completed_by_name ? <p className="text-xs text-slate-500">Registrado por {response.completed_by_name}</p> : null}</div>
      {response ? <div className="flex gap-2"><Button disabled={busy || Boolean(response.corrective_incident_id)} onClick={() => open("incident")} size="sm" variant="secondary">{response.corrective_incident_id ? "Incidencia creada" : "Crear incidencia"}</Button><Button disabled={busy || Boolean(response.corrective_task_id)} onClick={() => open("task")} size="sm" variant="secondary">{response.corrective_task_id ? "Tarea creada" : "Tarea correctiva"}</Button></div> : null}
    </div>
    {evidences.map((evidence) => <Button key={evidence.id} onClick={() => setPreviewEvidence(evidence)} size="sm" variant="ghost">Ver {evidence.original_filename}</Button>)}
    <LogbookDialog busy={processing} confirmDisabled={!title.trim() || (kind === "task" && !assignee)} confirmLabel={kind === "incident" ? "Crear incidencia" : "Crear tarea correctiva"} description={`Origen: “${item.title}”. Se copiarán la observación y ${evidenceIds.length} evidencia(s) seleccionada(s).`} error={error} onClose={() => setKind(null)} onConfirm={() => void create()} open={Boolean(kind)} title={kind === "incident" ? "Crear incidencia" : "Crear tarea correctiva"}>
      <div className="space-y-3">
        <label className="grid gap-1 text-sm font-medium">Título<input autoFocus className="rounded-xl border p-3" maxLength={180} onChange={(event) => setTitle(event.target.value)} value={title}/></label>
        {kind === "task" ? <><label className="grid gap-1 text-sm font-medium">Responsable<select className="rounded-xl border p-3" onChange={(event) => setAssignee(event.target.value)} value={assignee}>{staff.filter((member) => member.user).map((member) => <option key={member.user_id} value={member.user_id}>{member.user?.full_name}</option>)}</select></label><label className="grid gap-1 text-sm font-medium">Fecha límite<input className="rounded-xl border p-3" onChange={(event) => setScheduled(event.target.value)} type="datetime-local" value={scheduled}/></label></> : null}
        <label className="grid gap-1 text-sm font-medium">Prioridad<select className="rounded-xl border p-3" onChange={(event) => setPriority(event.target.value)} value={priority}>{["LOW","MEDIUM","HIGH","CRITICAL"].map((value) => <option key={value} value={value}>{logbookLabel({LOW:"Baja",MEDIUM:"Media",HIGH:"Alta",CRITICAL:"Crítica"}, value)}</option>)}</select></label>
        {evidences.length ? <fieldset className="rounded-xl border p-3"><legend className="text-sm font-medium">Evidencias</legend>{evidences.map((evidence) => <label className="mt-2 flex items-center gap-2 text-sm" key={evidence.id}><input checked={evidenceIds.includes(evidence.id)} onChange={(event) => setEvidenceIds((current) => event.target.checked ? [...current, evidence.id] : current.filter((id) => id !== evidence.id))} type="checkbox"/>{evidence.original_filename}</label>)}</fieldset> : null}
      </div>
    </LogbookDialog>
    <LogbookEvidencePreview evidence={previewEvidence} onClose={() => setPreviewEvidence(null)} />
  </article>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-slate-50 p-2 text-center"><strong>{value}%</strong><p className="text-xs text-slate-500">{label}</p></div>; }
function Count({ label, value }: { label: string; value: number }) { return <div className="rounded-lg bg-slate-50 p-2 text-center"><strong>{value}</strong><p className="text-xs text-slate-500">{label}</p></div>; }
function ApprovalRequirements({ summary }: { summary: ReturnType<typeof validateLogbook> }) {
  const groups = [
    ["Respuestas obligatorias", summary.pendingRequiredResponses],
    ["Comentarios requeridos", summary.pendingComments],
    ["Evidencias obligatorias", summary.pendingEvidences],
    ["Evidencias por incumplimiento", summary.pendingFailureEvidences],
  ] as const;
  return <div className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900"><strong>No se puede aprobar todavía:</strong>{groups.filter(([, items]) => items.length).map(([label, items]) => <div className="mt-2" key={label}><p className="font-medium">{label}</p><ul className="list-disc pl-5">{items.map((item) => <li key={`${label}-${item.itemId}`}>{item.sectionTitle}: {item.itemTitle}</li>)}</ul></div>)}</div>;
}
function History({ assignment }: { assignment: Assignment }) { return <section className="rounded-2xl border bg-white p-4"><h3 className="font-semibold">Historial</h3>{assignment.history.map((entry) => <div className="mt-2 border-t pt-2 text-sm" key={entry.id}><strong>{entry.action}</strong> · intento {entry.attempt_number}<p className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString("es-CL")} · {logbookLabel(logbookStatusLabels, entry.previous_status)} → {logbookLabel(logbookStatusLabels, entry.new_status)}</p>{entry.comment ? <p>{entry.comment}</p> : null}</div>)}</section>; }
