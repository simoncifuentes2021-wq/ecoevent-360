"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy, ExternalLink, Eye, Plus, QrCode } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { BikeZoneVerifier } from "@/components/bike-zone/BikeZoneVerifier";
import { FormsSessionComparison } from "@/components/event-forms/FormsSessionComparison";
import { FormQrDialog } from "@/components/event-forms/FormQrDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { closeEventForm, createEventForm, getEventFormResponses, getEventForms, getEventFormSummary, publishEventForm } from "@/lib/api/eventForms";
import { getEventSessions } from "@/lib/api/eventSessions";
import type { EventForm, EventFormSummary, EventFormType, FormResponse } from "@/types/eventForm";
import type { EventSession } from "@/types/eventSession";
import type { UserRole } from "@/types/roles";

const typeLabels: Record<EventFormType, string> = {
  TRANSPORT_SURVEY: "Transporte publico",
  STAFF_TRANSPORT_SURVEY: "Transporte personal",
  BIKE_ZONE_REGISTRATION: "Bike Zone",
  EXPERIENCE_SURVEY: "Experiencia",
  CUSTOM: "Personalizado"
};

export function EventFormsTab({ eventId, role }: { eventId: string; role?: UserRole | null }) {
  const [forms, setForms] = useState<EventForm[]>([]);
  const [sessions, setSessions] = useState<EventSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [selected, setSelected] = useState<EventForm | null>(null);
  const [qrForm, setQrForm] = useState<EventForm | null>(null);
  const [summary, setSummary] = useState<EventFormSummary | null>(null);
  const [responses, setResponses] = useState<FormResponse[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    title: "",
    form_type: "TRANSPORT_SURVEY" as EventFormType,
    session_id: "",
    banner_url: "",
    primary_logo_url: "",
    secondary_logo_url: "",
    primary_color: "#16b86a",
    requires_language_selection: true,
    available_languages: ["es", "en", "pt", "ko"]
  });
  const canManage = role === "SUPER_ADMIN" || role === "ADMIN" || role === "SUPERVISOR";
  const canDeleteQr = role === "SUPER_ADMIN" || role === "ADMIN";

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [formData, sessionData] = await Promise.all([getEventForms(eventId), getEventSessions(eventId).catch(() => [])]);
      setForms(formData.items);
      setSessions(sessionData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los formularios.");
    } finally {
      setLoading(false);
    }
  }, [eventId]);

  useEffect(() => { void load(); }, [load]);

  const baseUrl = useMemo(() => typeof window === "undefined" ? "" : window.location.origin, []);

  async function submit() {
    await createEventForm(eventId, {
      ...form,
      session_id: form.session_id || null,
      banner_url: form.banner_url || null,
      primary_logo_url: form.primary_logo_url || null,
      secondary_logo_url: form.secondary_logo_url || null,
      default_language: "es",
      generate_template: true
    });
    setOpen(false);
    setForm({ title: "", form_type: "TRANSPORT_SURVEY", session_id: "", banner_url: "", primary_logo_url: "", secondary_logo_url: "", primary_color: "#16b86a", requires_language_selection: true, available_languages: ["es", "en", "pt", "ko"] });
    await load();
  }

  async function copyLink(item: EventForm) {
    await navigator.clipboard.writeText(`${baseUrl}/f/${item.public_slug}`);
  }

  async function loadDetails(item: EventForm) {
    setSelected(item);
    setDetailLoading(true);
    setDetailError(null);
    try {
      const [nextSummary, nextResponses] = await Promise.all([
        getEventFormSummary(item.id),
        getEventFormResponses(item.id)
      ]);
      setSummary(nextSummary);
      setResponses(nextResponses);
    } catch (err) {
      setDetailError(err instanceof Error ? err.message : "No se pudieron cargar las respuestas.");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-950">Formularios propios</h2>
          <p className="text-sm text-slate-600">Crea formularios públicos sin Google Forms ni importación CSV.</p>
        </div>
        {canManage ? <Button onClick={() => setOpen(true)} type="button"><Plus className="h-4 w-4" />Crear formulario</Button> : null}
      </div>
      {canManage ? <BikeZoneVerifier /> : null}
      <FormsSessionComparison eventId={eventId} />
      {loading ? <LoadingState label="Cargando formularios..." /> : null}
      {error ? <ErrorState message={error} onRetry={load} /> : null}
      {!loading && !error ? (
        <div className="grid gap-3 xl:grid-cols-2">
          {forms.map((item) => (
            <article className={`rounded-lg border bg-white p-4 shadow-sm ${selected?.id === item.id ? "border-emerald-500 ring-2 ring-emerald-100" : ""}`} key={item.id}>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-slate-950">{item.title}</h3>
                  <p className="text-sm text-slate-600">{typeLabels[item.form_type]} · {item.status} · {item.fields?.length ?? 0} campos</p>
                  <p className="mt-1 text-xs font-semibold text-emerald-700">/f/{item.public_slug}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" type="button" variant="secondary" onClick={() => copyLink(item)}><Copy className="h-4 w-4" />Copiar</Button>
                  <Button size="sm" type="button" variant="secondary" onClick={() => window.open(`/f/${item.public_slug}`, "_blank")}><ExternalLink className="h-4 w-4" />Abrir</Button>
                  <Button size="sm" type="button" variant="secondary" onClick={() => setQrForm(item)}><QrCode className="h-4 w-4" />QR</Button>
                  <Button size="sm" type="button" variant="secondary" onClick={() => loadDetails(item)}><Eye className="h-4 w-4" />Respuestas</Button>
                  {canManage && item.status !== "ACTIVE" ? <Button size="sm" type="button" onClick={async () => { await publishEventForm(item.id); await load(); }}>Publicar</Button> : null}
                  {canManage && item.status === "ACTIVE" ? <Button size="sm" type="button" variant="secondary" onClick={async () => { await closeEventForm(item.id); await load(); }}>Cerrar</Button> : null}
                </div>
              </div>
              <button
                className="mt-4 flex w-full items-center justify-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm font-bold text-emerald-800 transition hover:bg-emerald-100"
                type="button"
                onClick={() => loadDetails(item)}
              >
                <Eye className="h-4 w-4" />
                Ver respuestas y resumen
              </button>
            </article>
          ))}
          {!forms.length ? <p className="text-sm text-slate-500">Aún no hay formularios propios.</p> : null}
        </div>
      ) : null}
      {selected ? (
        <section className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-bold text-slate-950">Respuestas: {selected.title}</h3>
              <p className="text-sm text-slate-600">Registro de envíos recibidos desde el formulario público.</p>
            </div>
            <Button size="sm" type="button" variant="secondary" onClick={() => loadDetails(selected)}>Actualizar</Button>
          </div>
          {detailLoading ? <LoadingState label="Cargando respuestas..." /> : null}
          {detailError ? <ErrorState message={detailError} /> : null}
          {!detailLoading && !detailError ? (
            <div className="mt-4 space-y-4">
              <div className={`grid gap-3 ${selected.form_type === "BIKE_ZONE_REGISTRATION" ? "md:grid-cols-4" : "md:grid-cols-1"}`}>
                <Metric label="Total respuestas" value={summary?.total_responses ?? responses.length} />
                {selected.form_type === "BIKE_ZONE_REGISTRATION" ? (
                  <>
                    <Metric label="Bike Zone" value={summary?.bike_zone_total ?? 0} />
                    <Metric label="Check-in" value={summary?.bike_zone_checked_in ?? 0} />
                    <Metric label="Check-out" value={summary?.bike_zone_checked_out ?? 0} />
                  </>
                ) : null}
              </div>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                    <tr>
                      <th className="px-3 py-2">Fecha</th>
                      <th className="px-3 py-2">Idioma</th>
                      <th className="px-3 py-2">Nombre</th>
                      <th className="px-3 py-2">Email</th>
                      <th className="px-3 py-2">Código</th>
                      <th className="px-3 py-2">Datos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {responses.map((response) => (
                      <tr className="border-t align-top" key={response.id}>
                        <td className="px-3 py-2">{response.submitted_at ? new Date(response.submitted_at).toLocaleString("es-CL") : "-"}</td>
                        <td className="px-3 py-2 font-semibold">{response.language}</td>
                        <td className="px-3 py-2">{response.respondent_name || "-"}</td>
                        <td className="px-3 py-2">{response.respondent_email || "-"}</td>
                        <td className="px-3 py-2">{response.response_code || "-"}</td>
                        <td className="max-w-md px-3 py-2">
                          <pre className="max-h-32 overflow-auto rounded-md bg-slate-50 p-2 text-xs">{JSON.stringify(response.raw_data, null, 2)}</pre>
                        </td>
                      </tr>
                    ))}
                    {!responses.length ? <tr><td className="px-3 py-5 text-center text-slate-500" colSpan={6}>Todavía no hay respuestas para este formulario.</td></tr> : null}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </section>
      ) : null}
      {open ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/40 p-4">
          <div className="w-full max-w-2xl rounded-lg bg-white p-5 shadow-2xl">
            <h3 className="text-lg font-bold">Crear formulario propio</h3>
            <div className="mt-4 grid gap-3">
              <Input placeholder="Título del formulario" value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} />
              <div className="grid gap-3 md:grid-cols-2">
                <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.form_type} onChange={(event) => setForm({ ...form, form_type: event.target.value as EventFormType })}>
                  {Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                </select>
                <select className="h-10 rounded-md border bg-white px-3 text-sm" value={form.session_id} onChange={(event) => setForm({ ...form, session_id: event.target.value })}>
                  <option value="">Todo el evento</option>
                  {sessions.map((session) => <option key={session.id} value={session.id}>{session.name}</option>)}
                </select>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <Input placeholder="Banner URL" value={form.banner_url} onChange={(event) => setForm({ ...form, banner_url: event.target.value })} />
                <Input placeholder="Logo principal URL" value={form.primary_logo_url} onChange={(event) => setForm({ ...form, primary_logo_url: event.target.value })} />
              </div>
              <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                <Input placeholder="Logo secundario URL" value={form.secondary_logo_url} onChange={(event) => setForm({ ...form, secondary_logo_url: event.target.value })} />
                <Input className="w-24" type="color" value={form.primary_color} onChange={(event) => setForm({ ...form, primary_color: event.target.value })} />
              </div>
              <label className="flex items-center gap-2 text-sm font-semibold">
                <input checked={form.requires_language_selection} type="checkbox" onChange={(event) => setForm({ ...form, requires_language_selection: event.target.checked })} />
                Mostrar selección de idioma antes de responder
              </label>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button disabled={!form.title} type="button" onClick={submit}>Crear con plantilla</Button>
            </div>
          </div>
        </div>
      ) : null}
      {qrForm ? <FormQrDialog canDelete={canDeleteQr} form={qrForm} onClose={() => setQrForm(null)} /> : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <p className="text-xs font-bold uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-black text-slate-950">{value}</p>
    </div>
  );
}
