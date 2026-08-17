"use client";

import { CalendarDays, CheckCircle2, ClipboardCheck, Clock3, LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { EmptyState } from "@/components/common/EmptyState";
import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { PageHeader } from "@/components/common/PageHeader";
import { getMyLogbooks } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import { logbookLabel, logbookStatusLabels } from "@/lib/logbook-labels";
import type { LogbookAssignment } from "@/types/logbook";

const filters = ["ALL", "PENDING", "IN_PROGRESS", "SUBMITTED", "RESUBMITTED", "CHANGES_REQUESTED", "APPROVED", "OVERDUE"];
const editableAssignments = new Set(["PENDING", "IN_PROGRESS", "CHANGES_REQUESTED"]);
const editableInstances = new Set(["OPEN", "IN_PROGRESS", "CHANGES_REQUESTED"]);

export function MyLogbooksPage() {
  const [items, setItems] = useState<LogbookAssignment[]>([]);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = () => { setLoading(true); setError(""); getMyLogbooks(filter === "ALL" ? undefined : filter).then(setItems).catch(reason => setError(logbookError(reason, "No se pudieron cargar tus bitácoras."))).finally(() => setLoading(false)); };
  useEffect(load, [filter]);
  return <div className="space-y-6"><PageHeader title="Mis bitácoras" description="Revisa tus fechas y entra solo a las bitácoras disponibles."/><select className="w-full rounded-xl border bg-white p-3 md:w-72" value={filter} onChange={event => setFilter(event.target.value)}>{filters.map(value => <option key={value} value={value}>{value === "ALL" ? "Todos los estados" : logbookLabel(logbookStatusLabels, value)}</option>)}</select>{loading ? <LoadingState/> : error ? <ErrorState message={error} onRetry={load}/> : items.length === 0 ? <EmptyState icon={<ClipboardCheck/>} title="No hay bitácoras para este filtro" description="Las nuevas asignaciones aparecerán aquí."/> : <div className="space-y-3">{[...items].sort(compareAvailability).map(item => <WorkerLogbookCard item={item} key={item.id}/>)}</div>}</div>;
}

function canWork(item: LogbookAssignment) {
  if (!item.instance || !editableAssignments.has(item.status) || !editableInstances.has(item.instance.status)) return false;
  return item.instance.status !== "CHANGES_REQUESTED" || item.status === "CHANGES_REQUESTED";
}

function compareAvailability(left: LogbookAssignment, right: LogbookAssignment) {
  const availability = Number(canWork(right)) - Number(canWork(left));
  return availability || (left.instance?.occurrence_date || left.instance?.opens_at || "").localeCompare(right.instance?.occurrence_date || right.instance?.opens_at || "");
}

function formatDate(value?: string, withTime = false) {
  if (!value) return "Sin fecha";
  const parsed = value.length === 10 ? new Date(`${value}T12:00:00`) : new Date(value);
  return new Intl.DateTimeFormat("es-CL", { timeZone: "America/Santiago", dateStyle: "medium", ...(withTime ? { timeStyle: "short" as const } : {}) }).format(parsed);
}

function availability(item: LogbookAssignment) {
  if (canWork(item)) return { label: "Disponible para trabajar", detail: "Puedes registrar actividades ahora", card: "border-emerald-400 bg-emerald-50", badge: "bg-emerald-100 text-emerald-800", Icon: CheckCircle2 };
  if (item.instance?.status === "SCHEDULED") return { label: "Aún no disponible", detail: `Disponible desde ${formatDate(item.instance.opens_at, true)}`, card: "border-slate-200 bg-white", badge: "bg-blue-50 text-blue-800", Icon: Clock3 };
  if (item.instance?.status === "OVERDUE") return { label: "Plazo vencido", detail: `Venció ${formatDate(item.instance.due_at, true)}`, card: "border-amber-200 bg-amber-50/40", badge: "bg-amber-100 text-amber-900", Icon: LockKeyhole };
  return { label: "Solo consulta", detail: `Estado: ${logbookLabel(logbookStatusLabels, item.instance?.status || item.status)}`, card: "border-slate-200 bg-slate-50", badge: "bg-slate-200 text-slate-700", Icon: LockKeyhole };
}

function WorkerLogbookCard({ item }: { item: LogbookAssignment }) {
  const state = availability(item); const instance = item.instance; const Icon = state.Icon;
  return <article className={`rounded-xl border p-4 ${state.card}`}><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold text-slate-900">{instance?.name || "Bitácora asignada"}</p><p className="mt-1 flex items-center gap-1 text-sm font-medium text-slate-700"><CalendarDays className="h-4 w-4"/>{formatDate(instance?.occurrence_date || instance?.opens_at)}</p></div><span className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-semibold ${state.badge}`}><Icon className="h-4 w-4"/>{state.label}</span></div><div className="mt-3 grid gap-1 text-xs text-slate-600 sm:grid-cols-2"><p>Apertura: <strong>{formatDate(instance?.opens_at, true)}</strong></p><p>Vencimiento: <strong>{formatDate(instance?.due_at, true)}</strong></p></div><p className="mt-2 text-sm font-medium text-slate-700">{state.detail}</p><div className="mt-4 flex flex-wrap items-center justify-between gap-2"><p className="text-xs text-slate-500">{item.attempt_number > 1 ? "Reenvío" : "Envío inicial"} · Intento {item.attempt_number}</p><Link className={canWork(item) ? "inline-flex rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800" : "inline-flex rounded-xl border bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50"} href={`/worker/mis-bitacoras/${item.logbook_instance_id}`}>{canWork(item) ? "Entrar a trabajar" : "Ver programación"}</Link></div>{item.review_comment ? <p className="mt-3 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">{item.review_comment}</p> : null}</article>;
}
