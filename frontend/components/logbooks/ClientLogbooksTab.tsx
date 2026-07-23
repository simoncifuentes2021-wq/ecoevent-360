"use client";

import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { LogbookEvidencePreview } from "@/components/logbooks/LogbookEvidencePreview";
import { Button } from "@/components/ui/button";
import { getClientLogbook, getEventLogbooks } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import { logbookLabel, logbookStageLabels, logbookStatusLabels } from "@/lib/logbook-labels";
import type { ClientLogbookSummary, LogbookEvidence } from "@/types/logbook";

export function ClientLogbooksTab({ eventId }: { eventId: string }) {
  const [items, setItems] = useState<ClientLogbookSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [previewEvidence, setPreviewEvidence] = useState<LogbookEvidence | null>(null);

  async function load() {
    setLoading(true); setError("");
    try {
      const list = await getEventLogbooks(eventId);
      setItems(await Promise.all(list.items.map((item) => getClientLogbook(item.id))));
    } catch (reason) {
      setError(logbookError(reason, "No se pudieron cargar las bitácoras autorizadas."));
    } finally { setLoading(false); }
  }
  useEffect(() => { void load(); }, [eventId]);
  if (loading) return <LoadingState/>;
  if (error) return <ErrorState message={error} onRetry={load}/>;
  if (!items.length) return <EmptyState title="Sin bitácoras públicas" description="No hay procedimientos autorizados para este evento."/>;

  return <><div className="grid gap-4 md:grid-cols-2">{items.map((item) => <article className="rounded-2xl border bg-white p-5" key={item.id}>
    <div className="flex justify-between gap-2"><h3 className="font-semibold">{item.name}</h3><span className="text-sm text-emerald-700">{logbookLabel(logbookStatusLabels,item.status)}</span></div>
    <p className="text-xs text-slate-500">{logbookLabel(logbookStageLabels,item.operational_stage)}</p>
    <div className="mt-4 h-2 overflow-hidden rounded bg-slate-200"><div className="h-full bg-emerald-600" style={{width:`${item.completion_percentage}%`}}/></div>
    <p className="mt-2 text-sm">{item.completion_percentage}% de cumplimiento</p>
    <div className="mt-2 grid grid-cols-3 gap-2 text-center text-xs"><span>{item.completion_percentage}%<br/>Cumplimiento</span><span>{item.participation_percentage}%<br/>Participación</span><span>{item.approval_percentage}%<br/>Aprobación</span></div>
    <div className="mt-3 grid grid-cols-3 text-center text-xs"><span>{item.total_required_items}<br/>Obligatorios</span><span>{item.completed_items}<br/>Completados</span><span>{item.failed_items}<br/>Observados</span></div>
    {item.public_evidences.length ? <div className="mt-3"><p className="text-xs text-slate-500">{item.public_evidences.length} evidencias públicas disponibles</p><div className="mt-2 flex flex-wrap gap-2">{item.public_evidences.map((evidence) => <Button key={evidence.id} onClick={() => setPreviewEvidence(evidence)} size="sm" variant="secondary">Ver {evidence.original_filename}</Button>)}</div></div> : null}
  </article>)}</div><LogbookEvidencePreview evidence={previewEvidence} onClose={() => setPreviewEvidence(null)}/></>;
}
