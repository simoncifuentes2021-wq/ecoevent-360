"use client";
/* eslint-disable react-hooks/exhaustive-deps -- Reload is keyed by instance identity. */
/* eslint-disable @next/next/no-img-element -- Private signed URLs are short-lived and cannot use the image optimizer. */
import { useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  deleteContributionEvidence, getContributionEvidenceAccess, getDailyLogbookMetrics,
  getMaterializedLogbookItems, saveMyLogbookContribution, uploadContributionEvidence,
} from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import type { DailyLogbookMetrics, LogbookContributionEvidence, LogbookInstanceItem } from "@/types/logbook";

type Filter = "ALL" | "EMPTY" | "WITH" | "MINE" | "EVIDENCE";

export function DailyContributionList({ instanceId, userId, disabled, management = false }: {
  instanceId: string; userId: string; disabled: boolean; management?: boolean;
}) {
  const [items, setItems] = useState<LogbookInstanceItem[]>([]);
  const [metrics, setMetrics] = useState<DailyLogbookMetrics | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState<Filter>("ALL");
  const [preview, setPreview] = useState<string | null>(null);

  async function load() {
    try {
      const [nextItems, nextMetrics] = await Promise.all([
        getMaterializedLogbookItems(instanceId), getDailyLogbookMetrics(instanceId),
      ]);
      setItems(nextItems); setMetrics(nextMetrics);
    } catch (cause) { setError(logbookError(cause)); }
  }
  useEffect(() => { void load(); }, [instanceId]);
  const shown = useMemo(() => items.filter((item) =>
    filter === "ALL"
    || (filter === "EMPTY" && !item.contributions.length)
    || (filter === "WITH" && item.contributions.length > 0)
    || (filter === "MINE" && item.contributions.some((entry) => entry.author_id === userId))
    || (filter === "EVIDENCE" && item.contributions.some((entry) => entry.evidences.length)),
  ), [filter, items, userId]);

  async function showEvidence(evidence: LogbookContributionEvidence) {
    try { setPreview((await getContributionEvidenceAccess(evidence.id)).url); }
    catch (cause) { setError(logbookError(cause, "No se pudo abrir la fotografía.")); }
  }

  return <section className="space-y-4">
    <div><h2 className="text-lg font-semibold">Actividades programadas</h2><p className="text-sm text-slate-500">Una actividad cuenta como completada cuando existe al menos un aporte válido.</p></div>
    {metrics ? <MetricGrid metrics={metrics} /> : null}
    <div className="flex flex-wrap gap-2">{([[
      "ALL", "Todas"], ["EMPTY", "Sin actividad"], ["WITH", "Con aportes"],
      ["MINE", "Mis aportes"], ["EVIDENCE", "Con evidencia"],
    ] as Array<[Filter, string]>).map(([value, label]) => <Button key={value} onClick={() => setFilter(value)} size="sm" variant={filter === value ? "primary" : "secondary"}>{label}</Button>)}</div>
    {error ? <p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p> : null}
    {shown.map((item) => {
      const mine = item.contributions.find((entry) => entry.author_id === userId);
      return <article className="rounded-2xl border bg-white p-4" key={item.id}>
        <h3 className="font-semibold">{item.title}</h3>
        {!item.contributions.length ? <p className="mt-2 text-sm text-slate-500">Aún no hay aportes para esta actividad</p> : <div className="mt-2 space-y-2">{item.contributions.map((entry) => <div className={entry.author_id === userId ? "rounded-lg bg-emerald-50 p-3 text-sm" : "rounded-lg bg-slate-50 p-3 text-sm"} key={entry.id}>
          <strong>{entry.author_id === userId ? "Mi aporte" : entry.author_name || "Aporte del equipo"}</strong><p>{entry.description}</p><time className="text-xs text-slate-500">{new Date(entry.updated_at).toLocaleString("es-CL")}</time>
          <div className="mt-2 flex flex-wrap gap-2">{entry.evidences.map((evidence) => <span className="rounded border bg-white p-2 text-xs" key={evidence.id}><button className="text-emerald-700" onClick={() => void showEvidence(evidence)} type="button">Ver {evidence.original_filename}</button>{entry.author_id === userId && !disabled ? <button className="ml-2 text-red-600" onClick={async () => { try { await deleteContributionEvidence(evidence.id); await load(); } catch (cause) { setError(logbookError(cause)); } }} type="button">Eliminar</button> : null}</span>)}</div>
        </div>)}</div>}
        {!management ? <><label className="mt-3 block text-sm font-medium">¿Qué hiciste en esta actividad?<textarea className="mt-1 min-h-24 w-full rounded-xl border p-3" disabled={disabled || saving === item.id} onChange={(event) => setDrafts((current) => ({ ...current, [item.id]: event.target.value }))} value={drafts[item.id] ?? mine?.description ?? ""}/></label>
          <Button className="mt-2" disabled={disabled || saving === item.id || !(drafts[item.id] ?? mine?.description ?? "").trim()} onClick={async () => { setSaving(item.id); setError(""); try { await saveMyLogbookContribution(item.id, (drafts[item.id] ?? mine?.description ?? "").trim(), mine?.version); await load(); } catch (cause) { setError(logbookError(cause)); } finally { setSaving(null); } }}>{saving === item.id ? "Guardando…" : mine ? "Actualizar mi aporte" : "Guardar mi aporte"}</Button>
          {mine ? <label className="mt-2 block rounded-xl border border-dashed p-3 text-sm">Evidencia fotográfica<input accept="image/jpeg,image/png,image/webp" capture="environment" className="mt-2 block w-full" disabled={disabled} onChange={async (event) => { const file = event.target.files?.[0]; event.target.value = ""; if (!file) return; setSaving(item.id); try { await uploadContributionEvidence(mine.id, file); await load(); } catch (cause) { setError(logbookError(cause)); } finally { setSaving(null); } }} type="file"/></label> : null}</> : null}
      </article>;
    })}
    {preview ? <div className="fixed inset-0 z-50 grid place-items-center bg-black/70 p-4" onClick={() => setPreview(null)} role="presentation"><div className="max-h-[90vh] max-w-3xl rounded-xl bg-white p-3" onClick={(event) => event.stopPropagation()} role="presentation"><img alt="Evidencia del aporte" className="max-h-[75vh] w-auto rounded object-contain" src={preview}/><Button className="mt-3 w-full" onClick={() => setPreview(null)}>Cerrar</Button></div></div> : null}
  </section>;
}

function MetricGrid({ metrics }: { metrics: DailyLogbookMetrics }) {
  const values = [["Actividades", metrics.total_activities], ["Con aportes", metrics.activities_with_contributions], ["Sin actividad", metrics.activities_without_contributions], ["Aportes", metrics.contributions_count], ["Participantes", metrics.participants_assigned], ["Han aportado", metrics.participants_contributed], ["Fotografías", metrics.evidences_count], ["Avance", `${metrics.completion_percentage}%`]];
  return <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">{values.map(([label, value]) => <div className="rounded-xl bg-slate-50 p-3 text-center text-sm" key={label}><strong>{value}</strong><p className="text-xs text-slate-500">{label}</p></div>)}</div>;
}
