"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Clock3, History, RotateCcw, Send, XCircle } from "lucide-react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { getEnvironmentalReviewHistory } from "@/lib/api/environmental";
import type { EnvironmentalAction, EnvironmentalReview, EnvironmentalReviewDecision } from "@/types/environmental";

const statusLabels = { DRAFT: "Borrador", IN_REVIEW: "En revisión", APPROVED: "Aprobado", CHANGES_REQUESTED: "Con observaciones", REJECTED: "Rechazado" };
const decisionLabels = { SUBMITTED: "Enviado a revisión", APPROVED: "Aprobado", CHANGES_REQUESTED: "Cambios solicitados", REJECTED: "Rechazado", INVALIDATED: "Aprobación invalidada" };

export function EnvironmentalReviewPanel({ eventId, action, canManage, canReview, busy, onClose, onSubmit, onReview }: { eventId: string; action: EnvironmentalAction; canManage: boolean; canReview: boolean; busy: boolean; onClose: () => void; onSubmit: () => Promise<void>; onReview: (decision: EnvironmentalReviewDecision, comment?: string) => Promise<void> }) {
  const [history, setHistory] = useState<EnvironmentalReview[]>([]);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { getEnvironmentalReviewHistory(eventId, action.id).then(setHistory).catch((reason) => setError(reason instanceof Error ? reason.message : "No se pudo cargar el historial.")); }, [eventId, action.id]);
  async function decide(decision: EnvironmentalReviewDecision) { setError(null); if (decision !== "APPROVED" && !comment.trim()) { setError("Escribe el motivo para que quien registró la acción sepa qué corregir."); return; } await onReview(decision, comment.trim() || undefined); }
  return <ModalShell title="Revisión del impacto" description={`${action.name} · Revisión ${action.review_revision}`} onClose={onClose} size="lg">
    <div className="space-y-5">
      <section className="flex flex-col gap-3 rounded-2xl border bg-slate-50 p-4 sm:flex-row sm:items-center sm:justify-between"><div><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Estado de validación</p><p className="mt-1 text-lg font-bold">{statusLabels[action.review_status]}</p>{action.review_comment ? <p className="mt-1 text-sm text-slate-600">{action.review_comment}</p> : null}</div><ReviewIcon status={action.review_status} /></section>
      {canManage && action.review_status !== "IN_REVIEW" && action.review_status !== "APPROVED" ? <section className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4"><p className="text-sm text-emerald-900">Al enviar, un administrador validará los datos, la metodología, los factores y el resultado congelado.</p><Button className="mt-3" disabled={busy || action.status !== "CALCULATED"} onClick={() => void onSubmit()}><Send className="h-4 w-4" />Enviar a revisión</Button>{action.status !== "CALCULATED" ? <p className="mt-2 text-xs text-amber-700">Primero debes calcular correctamente la acción.</p> : null}</section> : null}
      {canReview && action.review_status === "IN_REVIEW" ? <section className="space-y-3 rounded-2xl border p-4"><label className="block text-sm font-semibold">Comentario de revisión<textarea className="mt-2 min-h-24 w-full rounded-xl border bg-white p-3 font-normal" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Opcional al aprobar; obligatorio al observar o rechazar" /></label><div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={() => void decide("APPROVED")}><CheckCircle2 className="h-4 w-4" />Aprobar</Button><Button variant="secondary" disabled={busy} onClick={() => void decide("CHANGES_REQUESTED")}><RotateCcw className="h-4 w-4" />Solicitar cambios</Button><Button variant="secondary" disabled={busy} onClick={() => void decide("REJECTED")}><XCircle className="h-4 w-4" />Rechazar</Button></div></section> : null}
      {error ? <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
      <section><h3 className="mb-3 flex items-center gap-2 font-bold"><History className="h-5 w-5 text-emerald-700" />Historial trazable</h3>{history.length ? <div className="space-y-2">{history.map((item) => <article className="rounded-xl border p-3" key={item.id}><div className="flex items-center justify-between gap-3"><p className="font-semibold">{decisionLabels[item.decision]}</p><span className="text-xs text-slate-500">Rev. {item.revision}</span></div><p className="mt-1 text-xs text-slate-500">{item.actor_name || "Usuario eliminado"} · {new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(item.created_at))}</p>{item.comment ? <p className="mt-2 text-sm text-slate-700">{item.comment}</p> : null}</article>)}</div> : <p className="text-sm text-slate-500">Aún no hay decisiones registradas.</p>}</section>
    </div>
  </ModalShell>;
}

function ReviewIcon({ status }: { status: EnvironmentalAction["review_status"] }) { const Icon = status === "APPROVED" ? CheckCircle2 : status === "REJECTED" ? XCircle : Clock3; return <Icon className={`h-9 w-9 ${status === "APPROVED" ? "text-emerald-600" : status === "REJECTED" ? "text-red-600" : "text-amber-600"}`} />; }
