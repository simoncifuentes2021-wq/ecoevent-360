"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowRight, FileClock, FilePlus2, Layers3, RefreshCw } from "lucide-react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { getEventSessions } from "@/lib/api/eventSessions";
import { getEvents } from "@/lib/api/events";
import { createReportDraft, getEventReports, updateReportDesign } from "@/lib/api/reports";
import type { Event } from "@/types/event";
import type { EventSession } from "@/types/eventSession";
import type { Report, ReportScope, ReportTemplateKey, ReportTheme } from "@/types/report";

const templateOptions: Array<{ value: ReportTemplateKey; label: string; description: string }> = [
  { value: "ENVIRONMENTAL_STORY", label: "Gestión ambiental premium", description: "Portada, reciclaje, Bike Zone, carbono, ecoequivalencias y evidencias." },
  { value: "ENVIRONMENTAL_PREMIUM", label: "Ambiental premium", description: "Informe ambiental completo con indicadores y gráficos." },
  { value: "COMPLETE", label: "Reporte completo", description: "Operación, formularios, incidencias y resultados ambientales." },
  { value: "EXECUTIVE", label: "Resumen ejecutivo", description: "Versión breve para dirección y cliente." },
  { value: "OPERATIONS", label: "Operaciones", description: "Staff, tareas, incidencias y cumplimiento." },
  { value: "BIKE_ZONE", label: "Bike Zone", description: "Reporte centrado en movilidad sostenible." },
];

const baseTheme: ReportTheme = { primary_color: "#12372A", secondary_color: "#2D6A4F", accent_color: "#95D5B2", background_color: "#F4F7F5", text_color: "#15231D", muted_color: "#61736A", cover_style: "DARK_OVERLAY", header_style: "MINIMAL", footer_style: "PAGE_NUMBER", show_page_numbers: true, show_event_name_in_footer: true };
const storyTheme: Partial<ReportTheme> = { primary_color: "#204D20", secondary_color: "#34883A", accent_color: "#69B849", background_color: "#EFFBE8", text_color: "#173D1B", muted_color: "#58705B" };

export function ReportCenter() {
  const router = useRouter();
  const [events, setEvents] = useState<Event[]>([]);
  const [eventId, setEventId] = useState("");
  const [scope, setScope] = useState<ReportScope>("EVENT");
  const [sessionId, setSessionId] = useState("");
  const [sessions, setSessions] = useState<EventSession[]>([]);
  const [template, setTemplate] = useState<ReportTemplateKey>("ENVIRONMENTAL_STORY");
  const [reports, setReports] = useState<Report[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadEvents = useCallback(async () => {
    setLoading(true); setError("");
    try {
      const response = await getEvents({ limit: 100 });
      setEvents(response.items);
      setEventId(current => current || response.items[0]?.id || "");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudieron cargar los eventos."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void loadEvents(); }, [loadEvents]);
  useEffect(() => {
    setSessionId(""); setSessions([]); setReports([]);
    if (!eventId) return;
    void Promise.all([getEventSessions(eventId), getEventReports(eventId)])
      .then(([availableSessions, availableReports]) => { setSessions(availableSessions); setReports(availableReports.items); })
      .catch(reason => setError(reason instanceof Error ? reason.message : "No se pudo cargar el evento."));
  }, [eventId]);

  const selectedEvent = useMemo(() => events.find(item => item.id === eventId), [eventId, events]);
  const selectedTemplate = templateOptions.find(item => item.value === template)!;

  async function create() {
    if (!eventId || (scope === "SHOW" && !sessionId)) return;
    setBusy(true); setError("");
    try {
      const draft = await createReportDraft(eventId, scope, scope === "SHOW" ? sessionId : undefined);
      const theme = { ...baseTheme, ...draft.theme, ...(template === "ENVIRONMENTAL_STORY" ? storyTheme : {}) } as ReportTheme;
      await updateReportDesign(draft.id, draft.edit_version, template, theme);
      router.push(`/reports/${draft.id}/edit`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo crear el borrador."); }
    finally { setBusy(false); }
  }

  return <div className="mx-auto max-w-7xl space-y-6">
    <header className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
      <div><p className="text-xs font-bold uppercase tracking-[.2em] text-emerald-600">Centro de reportes</p><h1 className="mt-1 text-3xl font-bold text-slate-950">Crea o continúa un reporte</h1><p className="mt-2 max-w-2xl text-sm text-slate-600">Este espacio es el acceso rápido global. Selecciona el evento, el alcance y una base editorial; después se abre el constructor completo.</p></div>
      <Button variant="secondary" disabled={loading} onClick={() => void loadEvents()}><RefreshCw className="h-4 w-4"/>Actualizar</Button>
    </header>
    {error ? <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div> : null}
    <section className="grid gap-5 lg:grid-cols-[1.1fr_.9fr]">
      <div className="rounded-3xl border bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3"><span className="rounded-2xl bg-emerald-100 p-3 text-emerald-700"><FilePlus2/></span><div><h2 className="text-xl font-bold">Nuevo reporte</h2><p className="text-sm text-slate-500">La plantilla carga y ordena sus secciones automáticamente.</p></div></div>
        <div className="mt-6 grid gap-5">
          <label className="text-sm font-semibold">1. Evento<select aria-label="Evento" className="mt-2 h-12 w-full rounded-xl border bg-white px-3 font-normal" value={eventId} onChange={event => setEventId(event.target.value)}><option value="">Selecciona un evento</option>{events.map(item => <option key={item.id} value={item.id}>{item.name} · {item.client?.business_name || "Sin cliente"}</option>)}</select></label>
          <fieldset><legend className="text-sm font-semibold">2. Alcance</legend><div className="mt-2 grid grid-cols-2 gap-3">{(["EVENT", "SHOW"] as const).map(value => <button key={value} type="button" onClick={() => setScope(value)} className={`rounded-2xl border p-4 text-left ${scope === value ? "border-emerald-500 bg-emerald-50" : "border-slate-200"}`}><b>{value === "EVENT" ? "Evento completo" : "Un show"}</b><span className="mt-1 block text-xs text-slate-500">{value === "EVENT" ? "Consolida todos los shows." : "Aísla solo ese show."}</span></button>)}</div></fieldset>
          {scope === "SHOW" ? <label className="text-sm font-semibold">Show<select aria-label="Show" className="mt-2 h-12 w-full rounded-xl border bg-white px-3 font-normal" value={sessionId} onChange={event => setSessionId(event.target.value)}><option value="">Selecciona un show</option>{sessions.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label> : null}
          <label className="text-sm font-semibold">3. Plantilla<select aria-label="Plantilla" className="mt-2 h-12 w-full rounded-xl border bg-white px-3 font-normal" value={template} onChange={event => setTemplate(event.target.value as ReportTemplateKey)}>{templateOptions.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select><span className="mt-2 block text-xs font-normal text-slate-500">{selectedTemplate.description}</span></label>
          <Button className="h-12" disabled={busy || !eventId || (scope === "SHOW" && !sessionId)} onClick={() => void create()}>{busy ? "Preparando constructor…" : "Crear y abrir constructor"}<ArrowRight className="h-4 w-4"/></Button>
        </div>
      </div>
      <aside className="rounded-3xl bg-slate-950 p-6 text-white"><Layers3 className="text-emerald-300"/><h2 className="mt-4 text-2xl font-bold">Flujo recomendado</h2><ol className="mt-5 space-y-4 text-sm text-slate-300"><li><b className="text-white">1. Base automática.</b> El motor copia los datos reales del evento o show.</li><li><b className="text-white">2. Edición segura.</b> Ajusta textos, imágenes, composición y elementos visibles sin modificar las tablas fuente.</li><li><b className="text-white">3. Revisión.</b> Comprueba el PDF exacto y guarda una revisión recuperable.</li><li><b className="text-white">4. Publicación.</b> Genera una versión PDF inmutable y luego entrégala al cliente.</li></ol>{selectedEvent ? <div className="mt-8 rounded-2xl bg-white/10 p-4"><p className="text-xs uppercase tracking-widest text-emerald-300">Evento activo</p><p className="mt-2 font-bold">{selectedEvent.name}</p><p className="text-sm text-slate-300">{selectedEvent.location_name || "Recinto por definir"}</p></div> : null}</aside>
    </section>
    <section className="rounded-3xl border bg-white p-6 shadow-sm"><div className="flex items-center gap-3"><FileClock className="text-emerald-600"/><div><h2 className="text-xl font-bold">Reportes de este evento</h2><p className="text-sm text-slate-500">Continúa un borrador o revisa una versión existente.</p></div></div><div className="mt-5 grid gap-3">{reports.length ? reports.map(report => <button key={report.id} type="button" onClick={() => router.push(`/reports/${report.id}/edit`)} className="flex items-center justify-between rounded-2xl border p-4 text-left transition hover:border-emerald-400 hover:bg-emerald-50"><span><b className="block">{report.title}</b><span className="text-xs text-slate-500">{report.scope === "SHOW" ? "Show" : "Evento"} · {report.template_key || "Sin plantilla"} · {report.status}</span></span><ArrowRight className="h-4 w-4"/></button>) : <p className="rounded-2xl bg-slate-50 p-5 text-sm text-slate-500">{eventId ? "Este evento aún no tiene reportes." : "Selecciona un evento para ver sus reportes."}</p>}</div></section>
  </div>;
}
