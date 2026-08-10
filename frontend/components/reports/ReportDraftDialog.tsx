"use client";

import { useEffect, useState } from "react";
import { FileText, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { getEventSessions } from "@/lib/api/eventSessions";
import type { EventSession } from "@/types/eventSession";
import type { ReportScope } from "@/types/report";

export function ReportDraftDialog({ eventId, open, loading, onClose, onCreate }: { eventId: string; open: boolean; loading: boolean; onClose: () => void; onCreate: (scope: ReportScope, sessionId?: string) => void }) {
  const [scope, setScope] = useState<ReportScope>("EVENT");
  const [sessionId, setSessionId] = useState("");
  const [sessions, setSessions] = useState<EventSession[]>([]);
  useEffect(() => { if (open) void getEventSessions(eventId).then(setSessions).catch(() => setSessions([])); }, [eventId, open]);
  if (!open) return null;
  return <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/50 p-4">
    <div className="w-full max-w-xl rounded-3xl bg-white p-6 shadow-2xl">
      <div className="flex items-start justify-between"><div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-600">Nuevo borrador</p><h2 className="mt-1 text-2xl font-bold text-slate-950">Constructor profesional</h2><p className="mt-2 text-sm text-slate-600">Elige el alcance. Los datos se copiarán a un snapshot editable.</p></div><button onClick={onClose} aria-label="Cerrar"><X /></button></div>
      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        {(["EVENT", "SHOW"] as ReportScope[]).map(value => <button key={value} type="button" onClick={() => setScope(value)} className={`rounded-2xl border p-4 text-left ${scope === value ? "border-emerald-500 bg-emerald-50" : "border-slate-200"}`}><FileText className="mb-3 h-5 w-5 text-emerald-600"/><strong>{value === "EVENT" ? "Evento completo" : "Show específico"}</strong><p className="mt-1 text-xs text-slate-500">{value === "EVENT" ? "Consolidado de toda la operación." : "Solo datos asociados al show."}</p></button>)}
      </div>
      {scope === "SHOW" ? <label className="mt-5 block text-sm font-semibold">Show<select className="mt-2 h-11 w-full rounded-lg border bg-white px-3" value={sessionId} onChange={e => setSessionId(e.target.value)}><option value="">Selecciona un show</option>{sessions.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : null}
      <div className="mt-7 flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={loading || (scope === "SHOW" && !sessionId)} onClick={() => onCreate(scope, sessionId || undefined)}>{loading ? "Creando…" : "Crear borrador"}</Button></div>
    </div>
  </div>;
}
