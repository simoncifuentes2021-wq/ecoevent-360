"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Copy, ExternalLink, Eye, Plus, QrCode } from "lucide-react";

import { ErrorState } from "@/components/common/ErrorState";
import { LoadingState } from "@/components/common/LoadingState";
import { BikeZoneVerifier } from "@/components/bike-zone/BikeZoneVerifier";
import { FormsSessionComparison } from "@/components/event-forms/FormsSessionComparison";
import { FormQrDialog } from "@/components/event-forms/FormQrDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { closeEventForm, createEventForm, getEventFormResponses, getEventForms, getEventFormSummary, publishEventForm } from "@/lib/api/eventForms";
import { getEvent } from "@/lib/api/events";
import { getEventSessions } from "@/lib/api/eventSessions";
import type { Event } from "@/types/event";
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
  const [event, setEvent] = useState<Event | null>(null);
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
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const creatingRef = useRef(false);
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
      const [eventData, formData, sessionData] = await Promise.all([getEvent(eventId), getEventForms(eventId), getEventSessions(eventId).catch(() => [])]);
      setEvent(eventData);
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
  const selectedSession = useMemo(() => sessions.find((session) => session.id === form.session_id) ?? null, [form.session_id, sessions]);

  async function submit() {
    if (creatingRef.current || !form.title.trim()) return;

    creatingRef.current = true;
    setCreating(true);
    setCreateError(null);
    try {
      await createEventForm(eventId, {
        ...form,
        title: form.title.trim(),
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
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : "No se pudo crear el formulario.");
    } finally {
      creatingRef.current = false;
      setCreating(false);
    }
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
        {canManage ? <Button disabled={creating} onClick={() => { setCreateError(null); setOpen(true); }} type="button"><Plus className="h-4 w-4" />Crear formulario</Button> : null}
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
          <div className="max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-lg bg-white p-5 shadow-2xl">
            <h3 className="text-lg font-bold">Crear formulario propio</h3>
            <p className="text-sm text-slate-600">Configura el formulario y revisa la vista previa antes de crearlo.</p>
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
            <FormCreationPreview event={event} form={form} session={selectedSession} />
            {createError ? <p className="mt-4 text-sm font-semibold text-red-600" role="alert">{createError}</p> : null}
            <div className="mt-5 flex justify-end gap-2">
              <Button disabled={creating} type="button" variant="secondary" onClick={() => setOpen(false)}>Cancelar</Button>
              <Button disabled={creating || !form.title.trim()} type="button" onClick={submit}>{creating ? "Creando..." : "Crear con plantilla"}</Button>
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

type DraftFormState = {
  title: string;
  form_type: EventFormType;
  session_id: string;
  banner_url: string;
  primary_logo_url: string;
  secondary_logo_url: string;
  primary_color: string;
  requires_language_selection: boolean;
  available_languages: string[];
};

type PreviewField = {
  key: string;
  label: string;
  placeholder: string;
  type?: "select";
  readonly?: boolean;
};

function FormCreationPreview({ event, session, form }: { event: Event | null; session: EventSession | null; form: DraftFormState }) {
  const title = form.title.trim() || typeLabels[form.form_type];
  const eventName = event?.name || "Nombre del evento";
  const venueName = session?.venue_name || event?.location_name || "Nombre del venue / recinto";
  const banner = form.banner_url || "https://images.unsplash.com/photo-1501281668745-f7f57925c3b4?auto=format&fit=crop&w=1600&q=80";
  const fields = previewFields(form.form_type, eventName, venueName);

  return (
    <section className="mt-5 overflow-hidden rounded-lg border border-slate-200 bg-slate-100">
      <div className="relative min-h-48 bg-slate-900 text-white">
        <img alt="" className="absolute inset-0 h-full w-full object-cover opacity-80" src={banner} />
        <div className="absolute inset-0 bg-gradient-to-b from-slate-950/25 to-slate-950/75" />
        <div className="relative flex min-h-48 flex-col justify-between p-5">
          <div className="flex flex-wrap items-center gap-2">
            {form.primary_logo_url ? <img alt="Logo principal" className="h-12 max-w-[160px] rounded-md bg-white object-contain p-2 shadow" src={form.primary_logo_url} /> : null}
            {form.secondary_logo_url ? <img alt="Logo secundario" className="h-12 max-w-[160px] rounded-md bg-white object-contain p-2 shadow" src={form.secondary_logo_url} /> : null}
          </div>
          <div>
            <span className="inline-flex rounded-md bg-white/95 px-3 py-1 text-sm font-bold text-slate-900">{title}</span>
            <h4 className="mt-3 max-w-3xl text-2xl font-black md:text-4xl">{eventName}</h4>
            <p className="mt-1 text-sm font-semibold text-white/90">{[session?.name, venueName].filter(Boolean).join(" - ")}</p>
          </div>
        </div>
      </div>
      {form.requires_language_selection ? (
        <div className="border-b border-slate-200 bg-white p-4">
          <p className="text-sm font-bold text-slate-900">Elige tu idioma para continuar</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-4">
            {["ES Espanol", "GB English", "BR Portugues", "KR Korean"].map((label) => (
              <button className="rounded-md border bg-slate-50 px-3 py-2 text-sm font-bold text-slate-700" key={label} type="button">{label}</button>
            ))}
          </div>
        </div>
      ) : null}
      <div className="bg-white p-4 md:p-6">
        <div className="mx-auto max-w-2xl rounded-lg border border-emerald-100 p-4 shadow-sm">
          <p className="mb-4 rounded-md border border-emerald-100 bg-emerald-50 p-3 text-sm font-semibold text-emerald-950">{previewDescription(form.form_type, eventName, venueName)}</p>
          <div className="space-y-3">
            {fields.map((field) => <PreviewControl field={field} key={field.key} />)}
          </div>
          <button className="mt-5 h-11 w-full rounded-md text-sm font-black text-white" style={{ backgroundColor: form.primary_color }} type="button">Enviar encuesta</button>
        </div>
      </div>
    </section>
  );
}

function PreviewControl({ field }: { field: PreviewField }) {
  return (
    <label className="block text-sm font-bold text-slate-800">
      {field.label}
      {field.type === "select" ? (
        <select className="mt-2 h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-600" value="" onChange={() => undefined}>
          <option>{field.placeholder}</option>
        </select>
      ) : (
        <input className={`mt-2 h-10 w-full rounded-md border border-slate-200 px-3 text-sm ${field.readonly ? "bg-slate-50 text-slate-600" : "bg-white text-slate-900"}`} placeholder={field.placeholder} readOnly={field.readonly} value={field.readonly ? field.placeholder : ""} onChange={() => undefined} />
      )}
    </label>
  );
}

function previewFields(type: EventFormType, eventName: string, venueName: string): PreviewField[] {
  const readonlyBase: PreviewField[] = [
    { key: "event_name", label: "Nombre del evento", placeholder: eventName, readonly: true },
    { key: "venue_name", label: "Nombre del venue / recinto", placeholder: venueName, readonly: true }
  ];
  if (type === "TRANSPORT_SURVEY") {
    return [...readonlyBase, { key: "full_name", label: "Nombre completo", placeholder: "Ej. Juan Perez" }, { key: "email", label: "Correo electronico", placeholder: "tucorreo@dominio.com" }, { key: "transport_mode", label: "Tipo de transporte utilizado para llegar", placeholder: "Selecciona una opcion", type: "select" }, { key: "country_residence", label: "Pais de residencia", placeholder: "Selecciona tu pais", type: "select" }];
  }
  if (type === "STAFF_TRANSPORT_SURVEY") {
    return [...readonlyBase, { key: "full_name", label: "Nombre completo", placeholder: "Ej. Juan Perez" }, { key: "company", label: "Empresa", placeholder: "Ej. ACME Touring" }, { key: "country_origin", label: "Pais de origen", placeholder: "Selecciona tu pais de origen", type: "select" }, { key: "transport_mode", label: "Tipo de transporte utilizado para llegar", placeholder: "Selecciona una opcion", type: "select" }];
  }
  if (type === "BIKE_ZONE_REGISTRATION") {
    return [...readonlyBase, { key: "full_name", label: "Nombre completo", placeholder: "Ej. Juan Perez" }, { key: "email", label: "Correo electronico", placeholder: "tucorreo@dominio.com" }, { key: "phone", label: "Numero de telefono", placeholder: "Ej. +56912345678" }, { key: "bike_brand", label: "Marca de bicicleta", placeholder: "Ej. Oxford, Giant, Trek..." }, { key: "bike_model", label: "Modelo de bicicleta", placeholder: "Ej. Sport, Urban..." }, { key: "bike_color", label: "Color de bicicleta", placeholder: "Ej. Rojo, Azul..." }, { key: "residence_region", label: "Region", placeholder: "Selecciona tu region", type: "select" }, { key: "event_ticket_number", label: "Numero de ticket del evento", placeholder: "Ej. 123456" }];
  }
  if (type === "EXPERIENCE_SURVEY") {
    return [{ key: "general_rating", label: "Evaluacion general", placeholder: "1 a 7" }, { key: "cleanliness_rating", label: "Limpieza", placeholder: "1 a 7" }, { key: "bathroom_rating", label: "Banos", placeholder: "1 a 7" }, { key: "would_recommend", label: "Recomendarias el evento", placeholder: "Selecciona", type: "select" }, { key: "main_problem", label: "Problema principal", placeholder: "Selecciona", type: "select" }, { key: "comments", label: "Comentarios", placeholder: "Escribe tus comentarios" }];
  }
  return [{ key: "custom", label: "Campo personalizado", placeholder: "Configurable despues de crear" }];
}

function previewDescription(type: EventFormType, eventName: string, venueName: string) {
  if (type === "BIKE_ZONE_REGISTRATION") return `Completa tus datos para registrar tu bicicleta en ${eventName}, en ${venueName}. Te enviaremos un PDF con tu QR personal.`;
  if (type === "STAFF_TRANSPORT_SURVEY") return "Esta encuesta de transporte para personal registra empresa, pais de origen y medio de llegada.";
  if (type === "TRANSPORT_SURVEY") return "Esta encuesta busca conocer los medios de transporte utilizados por quienes asisten al evento. Gracias por responder, toma menos de 1 minuto.";
  if (type === "EXPERIENCE_SURVEY") return "Ayudanos a evaluar la experiencia del evento y detectar oportunidades de mejora.";
  return "Formulario personalizado.";
}
