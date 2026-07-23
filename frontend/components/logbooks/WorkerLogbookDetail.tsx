"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { useToast } from "@/components/common/ToastProvider";
import { LogbookDialog } from "@/components/logbooks/LogbookDialog";
import { LogbookEvidencePreview } from "@/components/logbooks/LogbookEvidencePreview";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import {
  deleteLogbookEvidence,
  getLogbookInstance,
  saveLogbookResponse,
  submitLogbook,
  uploadLogbookEvidence,
} from "@/lib/api/logbooks";
import { logbookLabel, logbookStatusLabels } from "@/lib/logbook-labels";
import { logbookError } from "@/lib/logbook-errors";
import type { LogbookEvidence, LogbookInstanceDetail, LogbookItem, LogbookResponse } from "@/types/logbook";

export function WorkerLogbookDetail({ id }: { id: string }) {
  const router = useRouter();
  const { user } = useAuth();
  const { toast } = useToast();
  const [data, setData] = useState<LogbookInstanceDetail | null>(null);
  const [pageError, setPageError] = useState("");
  const [itemErrors, setItemErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [uploading, setUploading] = useState<string | null>(null);
  const [dialog, setDialog] = useState<"submit" | "delete" | "conflict" | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ evidence: LogbookEvidence; item: LogbookItem } | null>(null);
  const [previewEvidence, setPreviewEvidence] = useState<LogbookEvidence | null>(null);
  const [dialogError, setDialogError] = useState("");
  const [processing, setProcessing] = useState(false);

  const load = async () => {
    setPageError("");
    try {
      setData(await getLogbookInstance(id));
    } catch (reason) {
      setPageError(logbookError(reason, "No se pudo cargar la bitácora."));
    }
  };

  useEffect(() => {
    if (user?.role === "SUPERVISOR") {
      router.replace(`/supervisor/bitacoras/${id}`);
      return;
    }
    void load();
  }, [id, user?.role]);

  useEffect(() => {
    const refreshOnFocus = () => void load();
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") void load();
    };
    window.addEventListener("focus", refreshOnFocus);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refreshOnFocus);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [id]);

  const assignment = data?.assignments[0];
  const responses = useMemo(
    () => new Map(assignment?.responses.map((response) => [response.logbook_item_id, response]) || []),
    [assignment],
  );

  if (pageError) return <ErrorState message={pageError} onRetry={load} />;
  if (!data || !assignment) return <LoadingState />;

  const locked = !["PENDING", "IN_PROGRESS", "CHANGES_REQUESTED"].includes(assignment.status);
  const allItems = data.version.sections.flatMap((section) => section.items);
  const missingItems = allItems.filter((item) => {
    if (!item.is_required) return false;
    const response = responses.get(item.id);
    if (!response || response.result_status === "PENDING") return true;
    const evidenceCount = response.evidences.filter((evidence) => !evidence.deleted_at).length;
    return item.evidence_policy === "REQUIRED" && evidenceCount < Math.max(1, item.min_evidences);
  });
  const completedItems = allItems.length - missingItems.length;

  async function save(item: LogbookItem, patch: Partial<LogbookResponse>) {
    if (!assignment) return;
    setSaving(item.id);
    setItemErrors((current) => ({ ...current, [item.id]: "" }));
    try {
      const current = responses.get(item.id);
      await saveLogbookResponse(assignment.id, {
        item_id: item.id,
        result_status: patch.result_status ?? current?.result_status ?? "COMPLETED",
        selected_option_id: patch.selected_option_id ?? current?.selected_option_id ?? null,
        boolean_value: patch.boolean_value ?? current?.boolean_value ?? null,
        numeric_value: patch.numeric_value ?? current?.numeric_value ?? null,
        text_value: patch.text_value ?? current?.text_value ?? null,
        is_not_applicable: patch.is_not_applicable ?? current?.is_not_applicable ?? false,
        comment: patch.comment ?? current?.comment ?? null,
        version: current?.version,
      });
      await load();
      toast({ title: "Cambios guardados", tone: "success" });
    } catch (reason) {
      const conflict = reason instanceof ApiError && reason.status === 409;
      setItemErrors((current) => ({
        ...current,
        [item.id]: conflict
          ? "Esta respuesta cambió mientras trabajabas. Recarga antes de guardar."
          : logbookError(reason, "No se pudo guardar la respuesta."),
      }));
      if (conflict) {
        setDialogError("");
        setDialog("conflict");
      }
    } finally {
      setSaving(null);
    }
  }

  async function upload(item: LogbookItem, file: File) {
    if (!assignment) return;
    setUploading(item.id);
    setItemErrors((current) => ({ ...current, [item.id]: "" }));
    try {
      let response = responses.get(item.id);
      if (!response) {
        if (item.item_type !== "PHOTO") {
          throw new Error("Primero debes responder este ítem antes de adjuntar una evidencia.");
        }
        response = await saveLogbookResponse(assignment.id, {
          item_id: item.id,
          result_status: "COMPLETED",
          is_not_applicable: false,
        });
      }
      await uploadLogbookEvidence(assignment.id, response.id, file);
      await load();
      toast({ title: "Evidencia subida", description: file.name, tone: "success" });
    } catch (reason) {
      setItemErrors((current) => ({
        ...current,
        [item.id]: logbookError(reason, "No se pudo subir la fotografía."),
      }));
    } finally {
      setUploading(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 pb-24">
      <header>
        <Button onClick={() => router.back()} variant="ghost">Volver</Button>
        <div className="mt-2 flex items-start justify-between gap-3">
          <h1 className="text-2xl font-bold">{data.name}</h1>
          {data.assignment_mode === "SHARED" ? <Button onClick={() => void load()} size="sm" variant="secondary">Actualizar</Button> : null}
        </div>
        <p className="text-sm text-slate-500">
          {logbookLabel(logbookStatusLabels, assignment.status)} · Intento {assignment.attempt_number}
        </p>
        {data.assignment_mode === "SHARED" ? <p className="mt-1 text-xs text-emerald-700">Bitácora compartida · las respuestas muestran el último cambio del equipo.</p> : null}
        {assignment.review_comment ? <p className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900">{assignment.review_comment}</p> : null}
        <div className="mt-3 h-2 overflow-hidden rounded bg-slate-200">
          <div className="h-full bg-emerald-600" style={{ width: `${data.metrics.completion_percentage}%` }} />
        </div>
        <p className="mt-1 text-sm text-slate-500">{data.metrics.completion_percentage}% completado · {saving ? "Guardando…" : "Cambios guardados"}</p>
      </header>

      {data.version.sections.map((section) => (
        <section className="rounded-2xl border bg-white p-4" key={section.id}>
          <h2 className="text-lg font-semibold">{section.title}</h2>
          <div className="mt-4 space-y-5">
            {section.items.map((item) => (
              <ItemField
                disabled={locked || saving === item.id}
                error={itemErrors[item.id]}
                item={item}
                key={item.id}
                response={responses.get(item.id)}
                uploading={uploading === item.id}
                onDeleteEvidence={(evidence) => {
                  setDeleteTarget({ evidence, item });
                  setDialogError("");
                  setDialog("delete");
                }}
                onPreviewEvidence={setPreviewEvidence}
                save={save}
                upload={(file) => upload(item, file)}
              />
            ))}
          </div>
        </section>
      ))}

      {assignment.history.length ? (
        <section className="rounded-2xl border bg-white p-4">
          <h2 className="font-semibold">Historial</h2>
          {assignment.history.map((entry) => (
            <div className="mt-2 border-t pt-2 text-sm" key={entry.id}>
              <strong>{entry.action === "SUBMIT" ? (entry.attempt_number > 1 ? "Reenvío" : "Envío") : entry.action}</strong>
              <p className="text-xs text-slate-500">{new Date(entry.created_at).toLocaleString("es-CL")} · Intento {entry.attempt_number}</p>
              {entry.comment ? <p>{entry.comment}</p> : null}
            </div>
          ))}
        </section>
      ) : null}

      {!locked ? (
        <Button
          className="fixed bottom-5 left-1/2 w-[min(90%,42rem)] -translate-x-1/2 shadow-xl"
          disabled={processing}
          onClick={() => { setDialogError(""); setDialog("submit"); }}
        >
          {assignment.status === "CHANGES_REQUESTED" ? "Reenviar a revisión" : "Enviar a revisión"}
        </Button>
      ) : null}
      <LogbookDialog
        busy={processing}
        confirmDisabled={missingItems.length > 0}
        confirmLabel={assignment.status === "CHANGES_REQUESTED" ? "Reenviar bitácora" : "Enviar bitácora"}
        description={assignment.status === "CHANGES_REQUESTED"
          ? "Esta es una corrección de la entrega anterior. Después de reenviarla quedará nuevamente bloqueada mientras el supervisor la revisa."
          : "Revisa tus respuestas antes de continuar. Después de enviar la bitácora no podrás modificarla, salvo que el supervisor solicite correcciones."}
        error={dialogError}
        onClose={() => setDialog(null)}
        onConfirm={async () => {
          if (processing) return;
          setProcessing(true); setDialogError("");
          try {
            await submitLogbook(assignment.id); await load(); setDialog(null);
            toast({ title: assignment.status === "CHANGES_REQUESTED" ? "Bitácora reenviada" : "Bitácora enviada", tone: "success" });
          } catch (reason) { setDialogError(logbookError(reason, "No se pudo enviar la bitácora.")); }
          finally { setProcessing(false); }
        }}
        open={dialog === "submit"}
        title="Enviar bitácora para revisión"
      >
        <div className="grid grid-cols-2 gap-3 rounded-2xl bg-slate-50 p-4 text-sm">
          <p>Tipo<br/><strong>{assignment.status === "CHANGES_REQUESTED" ? "Reenvío" : "Envío inicial"}</strong></p>
          <p>Intento<br/><strong>{assignment.attempt_number + 1}</strong></p>
          <p>Completadas<br/><strong>{completedItems} de {allItems.length}</strong></p>
          <p>Pendientes<br/><strong>{missingItems.length}</strong></p>
        </div>
        {missingItems.length ? <div className="mt-3 rounded-xl bg-amber-50 p-3 text-sm text-amber-900"><strong>Completa antes de enviar:</strong><ul className="list-disc pl-5">{missingItems.map((item) => <li key={item.id}>{item.title}</li>)}</ul></div> : null}
      </LogbookDialog>
      <LogbookDialog
        busy={processing}
        confirmLabel="Eliminar fotografía"
        description={`La fotografía “${deleteTarget?.evidence.original_filename || ""}” dejará de formar parte de esta respuesta.`}
        error={dialogError}
        onClose={() => setDialog(null)}
        onConfirm={async () => {
          if (!deleteTarget || processing) return;
          setProcessing(true); setDialogError("");
          try { await deleteLogbookEvidence(deleteTarget.evidence.id); await load(); setDialog(null); setDeleteTarget(null); toast({ title: "Evidencia eliminada", tone: "success" }); }
          catch (reason) { setDialogError(logbookError(reason, "No se pudo eliminar la fotografía.")); }
          finally { setProcessing(false); }
        }}
        open={dialog === "delete"}
        title="Eliminar fotografía"
        tone="danger"
      >
        {deleteTarget && (responses.get(deleteTarget.item.id)?.evidences.filter((evidence) => !evidence.deleted_at).length || 0) <= deleteTarget.item.min_evidences
          ? <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-900">Al eliminarla, la respuesta dejará de cumplir el mínimo obligatorio de evidencias.</p> : null}
      </LogbookDialog>
      <LogbookDialog
        confirmLabel="Recargar respuesta"
        description="Otro participante modificó esta respuesta mientras estabas trabajando. Recarga la versión más reciente antes de volver a guardar."
        onClose={() => setDialog(null)}
        onConfirm={async () => { await load(); setDialog(null); }}
        open={dialog === "conflict"}
        title="Esta respuesta fue actualizada"
        tone="warning"
      />
      <LogbookEvidencePreview evidence={previewEvidence} onClose={() => setPreviewEvidence(null)} />
    </div>
  );
}

function ItemField({
  item, response, disabled, error, uploading, save, upload, onDeleteEvidence, onPreviewEvidence,
}: {
  item: LogbookItem;
  response?: LogbookResponse;
  disabled: boolean;
  error?: string;
  uploading: boolean;
  save: (item: LogbookItem, patch: Partial<LogbookResponse>) => Promise<void>;
  upload: (file: File) => Promise<void>;
  onDeleteEvidence: (evidence: LogbookEvidence) => void;
  onPreviewEvidence: (evidence: LogbookEvidence) => void;
}) {
  const common = "mt-2 w-full rounded-xl border p-3";
  return (
    <div className="border-t pt-4 first:border-0 first:pt-0">
      <label className="font-medium">{item.title}{item.is_required ? " *" : ""}</label>
      {item.instructions ? <p className="text-sm text-slate-500">{item.instructions}</p> : null}
      {["CHECKBOX", "CONFIRMATION"].includes(item.item_type) ? (
        <label className="mt-2 flex items-center gap-2 text-sm">
          <input checked={response?.boolean_value ?? false} className="h-5 w-5" disabled={disabled} onChange={(event) => void save(item, { boolean_value: event.target.checked, is_not_applicable: false })} type="checkbox" />
          Confirmado
        </label>
      ) : null}
      {item.item_type === "YES_NO" ? (
        <select className={common} disabled={disabled} onChange={(event) => void save(item, event.target.value === "NA" ? { is_not_applicable: true } : { boolean_value: event.target.value === "YES", is_not_applicable: false })} value={response?.is_not_applicable ? "NA" : response?.boolean_value === true ? "YES" : response?.boolean_value === false ? "NO" : ""}>
          <option value="">Selecciona</option><option value="YES">Sí</option><option value="NO">No</option>
          {item.allow_not_applicable ? <option value="NA">No aplica</option> : null}
        </select>
      ) : null}
      {item.item_type === "STATUS_SELECT" ? (
        <select className={common} disabled={disabled} onChange={(event) => void save(item, { selected_option_id: event.target.value, is_not_applicable: false })} value={response?.selected_option_id || ""}>
          <option value="">Selecciona</option>
          {item.options.map((option) => <option key={option.id} value={option.id}>{option.label}</option>)}
        </select>
      ) : null}
      {item.item_type === "NUMBER" ? <input className={common} defaultValue={response?.numeric_value} disabled={disabled} onBlur={(event) => event.target.value && void save(item, { numeric_value: Number(event.target.value) })} type="number" /> : null}
      {["SHORT_TEXT", "LONG_TEXT"].includes(item.item_type) ? <textarea className={common} defaultValue={response?.text_value} disabled={disabled} onBlur={(event) => event.target.value && void save(item, { text_value: event.target.value })} rows={item.item_type === "LONG_TEXT" ? 5 : 2} /> : null}
      {item.item_type === "PHOTO" || item.evidence_policy !== "NONE" ? (
        <div className="mt-3 rounded-xl border border-dashed border-emerald-300 bg-emerald-50/50 p-3">
          <label className="text-sm font-medium text-emerald-900">
            {item.evidence_policy === "REQUIRED"
              ? "Evidencia fotográfica obligatoria"
              : item.evidence_policy === "REQUIRED_ON_FAILURE"
                ? "Evidencia obligatoria si existe un fallo"
                : "Evidencia fotográfica"}
          </label>
          <input
            accept="image/jpeg,image/png,image/webp"
            capture="environment"
            className="mt-2 block w-full text-sm"
            disabled={disabled || uploading}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void upload(file);
              event.target.value = "";
            }}
            type="file"
          />
          <p className="mt-1 text-xs text-slate-500">
            JPEG, PNG o WebP · mínimo {item.min_evidences} · máximo {item.max_evidences}
          </p>
        </div>
      ) : null}
      {uploading ? <p className="mt-1 text-sm text-emerald-700">Subiendo fotografía…</p> : null}
      {item.allow_not_applicable && item.item_type !== "YES_NO" ? <label className="mt-2 flex gap-2 text-sm"><input checked={response?.is_not_applicable || false} disabled={disabled} onChange={(event) => void save(item, { is_not_applicable: event.target.checked })} type="checkbox" />No aplica</label> : null}
      <textarea className={`${common} text-sm`} defaultValue={response?.comment} disabled={disabled} onBlur={(event) => void save(item, { comment: event.target.value })} placeholder="Comentario u observación" rows={2} />
      {error ? <p className="mt-2 rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        {response?.evidences.filter((evidence) => !evidence.deleted_at).map((evidence) => (
          <div className="rounded-lg border p-2 text-xs" key={evidence.id}>
            <button className="font-medium text-emerald-700" onClick={() => onPreviewEvidence(evidence)} type="button">Ver {evidence.original_filename}</button>
            {!disabled ? <button className="ml-3 text-red-600" onClick={() => onDeleteEvidence(evidence)} type="button">Eliminar</button> : null}
          </div>
        ))}
      </div>
      {dataModeAuthor(response)}
    </div>
  );
}

function dataModeAuthor(response?: LogbookResponse) {
  return response?.completed_by_name ? <p className="mt-1 text-xs text-slate-500">Registrado por {response.completed_by_name}</p> : null;
}
