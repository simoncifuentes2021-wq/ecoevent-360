"use client";

import { useEffect, useState } from "react";
import { CalendarDays, Leaf, LoaderCircle, Mail, MapPin, Recycle, Scale, Users } from "lucide-react";
import { getPublicActivation, getPublicVolunteerEvidenceUrl, getPublicVolunteerImpact, registerPublicVolunteer } from "@/lib/api/volunteers";
import type { PublicActivation, PublicVolunteerImpact } from "@/types/volunteer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const number = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 3 });
const date = (value: string) => new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short", timeZone: "America/Santiago" }).format(new Date(value));

export function PublicVolunteerRegistrationPage({ slug }: { slug: string }) {
  const [activation, setActivation] = useState<PublicActivation | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const [consent, setConsent] = useState(false);
  const [fields, setFields] = useState({ full_name: "", email: "", phone: "", organization: "" });

  useEffect(() => { let live = true; getPublicActivation(slug).then((row) => { if (live) setActivation(row); }).catch((reason) => { if (live) setError(reason instanceof Error ? reason.message : "No se pudo abrir la inscripción."); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [slug]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await registerPublicVolunteer(slug, fields);
      setDone(true);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No pudimos recibir tu inscripción. Revisa los datos e inténtalo nuevamente."); }
    finally { setBusy(false); }
  }

  return <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:py-12"><div className="mx-auto max-w-xl space-y-5">
    <header className="rounded-3xl bg-emerald-800 p-6 text-white shadow-sm"><div className="flex items-center gap-3"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-white/15"><Recycle /></span><div><p className="text-sm text-emerald-100">EcoEvent 360 · Inscripción de voluntarios</p><h1 className="text-xl font-bold">Súmate a la activación</h1></div></div></header>
    {loading ? <Panel><div className="flex items-center gap-3 text-slate-600"><LoaderCircle className="h-5 w-5 animate-spin" />Cargando información…</div></Panel> : null}
    {!loading && error && !activation ? <Panel><p role="alert" className="text-rose-700">{error}</p></Panel> : null}
    {activation ? <Panel><div><p className="text-xs font-semibold uppercase tracking-wide text-emerald-700">{activation.event_name}</p><h2 className="mt-1 text-2xl font-bold">{activation.name}</h2>{activation.description ? <p className="mt-2 text-slate-600">{activation.description}</p> : null}<div className="mt-4 grid gap-2 text-sm text-slate-600"><p className="flex gap-2"><CalendarDays className="h-4 w-4 shrink-0 text-emerald-700" />{date(activation.starts_at)}{activation.ends_at ? ` – ${date(activation.ends_at)}` : ""}</p>{activation.location_name || activation.address ? <p className="flex gap-2"><MapPin className="h-4 w-4 shrink-0 text-emerald-700" />{[activation.location_name, activation.address].filter(Boolean).join(" · ")}</p> : null}</div></div>
      {done ? <div className="mt-6 rounded-2xl bg-emerald-50 p-5 text-emerald-900"><h3 className="font-bold">Inscripción recibida</h3><p className="mt-1 text-sm">Si el correo está habilitado, recibirás una confirmación con un enlace privado para consultar tu aporte.</p></div> : activation.status !== "ACTIVE" ? <div className="mt-6 rounded-xl bg-amber-50 p-4 text-sm text-amber-900">Esta inscripción está cerrada por ahora.</div> : <form className="mt-6 space-y-4" onSubmit={submit}>
        <label className="grid gap-1.5 text-sm font-medium">Nombre completo<Input autoComplete="name" maxLength={180} required value={fields.full_name} onChange={(e) => setFields({ ...fields, full_name: e.target.value })} /></label>
        <label className="grid gap-1.5 text-sm font-medium">Correo electrónico<Input autoComplete="email" maxLength={254} required type="email" value={fields.email} onChange={(e) => setFields({ ...fields, email: e.target.value })} /></label>
        <label className="grid gap-1.5 text-sm font-medium">Teléfono<Input autoComplete="tel" maxLength={40} required type="tel" value={fields.phone} onChange={(e) => setFields({ ...fields, phone: e.target.value })} /></label>
        <label className="grid gap-1.5 text-sm font-medium">Organización (opcional)<Input maxLength={180} value={fields.organization} onChange={(e) => setFields({ ...fields, organization: e.target.value })} /></label>
        <label className="flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-sm leading-5"><input className="mt-1 h-4 w-4 accent-emerald-700" checked={consent} onChange={(e) => setConsent(e.target.checked)} required type="checkbox" /><span>{activation.consent_text}</span></label>
        {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800" role="alert">{error}</p> : null}
        <Button className="h-12 w-full" disabled={busy || !consent}>{busy ? "Enviando inscripción…" : "Inscribirme"}</Button>
        <p className="text-center text-xs text-slate-500">Consentimiento versión {activation.consent_version}.</p>
      </form>}
    </Panel> : null}<p className="text-center text-xs text-slate-400">Tus datos se usan para gestionar tu participación en esta iniciativa.</p>
  </div></main>;
}

export function PublicVolunteerImpactPage({ token }: { token: string }) {
  const [data, setData] = useState<PublicVolunteerImpact | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => { let live = true; getPublicVolunteerImpact(token).then((row) => { if (live) setData(row); }).catch((reason) => { if (live) setError(reason instanceof Error ? reason.message : "No se pudo abrir el historial."); }).finally(() => { if (live) setLoading(false); }); return () => { live = false; }; }, [token]);
  return <main className="min-h-screen bg-slate-50 px-4 py-8 text-slate-900 sm:py-12"><div className="mx-auto max-w-3xl space-y-5"><header className="rounded-3xl bg-emerald-800 p-6 text-white"><div className="flex items-center gap-3"><span className="grid h-12 w-12 place-items-center rounded-2xl bg-white/15"><Leaf /></span><div><p className="text-sm text-emerald-100">EcoEvent 360</p><h1 className="text-2xl font-bold">Mi aporte</h1></div></div></header>
    {loading ? <Panel><div className="flex items-center gap-3 text-slate-600"><LoaderCircle className="h-5 w-5 animate-spin" />Cargando tu historial…</div></Panel> : null}
    {error ? <Panel><p className="text-rose-700" role="alert">{error}</p><p className="mt-2 text-sm text-slate-500">Comprueba que el enlace esté completo. Por seguridad, este enlace privado no se puede reconstruir con tu correo o código.</p></Panel> : null}
    {data ? <><Panel><div><p className="text-sm text-slate-500">Hola,</p><h2 className="text-2xl font-bold">{data.full_name}</h2></div><div className="mt-5 grid gap-3 sm:grid-cols-3"><ImpactCard icon={<Scale />} label="Material recuperado" value={`${number.format(Number(data.total_weight_kg))} kg`} /><ImpactCard icon={<Users />} label="Activaciones" value={number.format(data.activation_count)} /><ImpactCard icon={<Mail />} label="Entregas" value={number.format(data.contribution_count)} /></div><div className="mt-5 flex flex-wrap gap-2">{Object.entries(data.material_totals).map(([name, weight]) => <span key={name} className="rounded-full bg-emerald-50 px-3 py-1.5 text-sm text-emerald-900">{name}: <b>{number.format(Number(weight))} kg</b></span>)}</div></Panel>
      <section className="space-y-3"><h2 className="px-1 text-lg font-bold">Tus entregas</h2>{data.contributions.length ? data.contributions.map((contribution, index) => <Panel key={contribution.id || `${contribution.registered_at}-${index}`}><div className="flex flex-wrap items-start justify-between gap-2"><div><h3 className="font-semibold">{contribution.activation}</h3><p className="text-sm text-slate-500">{contribution.event}</p></div><time className="text-sm text-slate-500">{date(contribution.registered_at)}</time></div><div className="mt-4 divide-y">{contribution.items.map((item, itemIndex) => <div className="flex justify-between py-2 text-sm" key={`${item.material}-${itemIndex}`}><span>{item.material}</span><b>{number.format(Number(item.weight_kg))} {item.unit}</b></div>)}</div><p className="mt-3 text-right font-bold text-emerald-800">Total: {number.format(Number(contribution.total_weight_kg))} kg</p>{contribution.evidences?.length ? <div className="mt-4 border-t pt-4"><h4 className="mb-3 text-sm font-semibold text-slate-700">Evidencia del aporte</h4><div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{contribution.evidences.map((evidence) => <a className="group overflow-hidden rounded-xl border bg-slate-50" href={getPublicVolunteerEvidenceUrl(token, evidence.id)} key={evidence.id} rel="noreferrer" target="_blank"><img alt={evidence.description || "Foto de evidencia de tu aporte"} className="aspect-square w-full object-cover transition group-hover:scale-[1.02]" loading="lazy" src={getPublicVolunteerEvidenceUrl(token, evidence.id)} /><span className="block truncate px-2 py-1.5 text-xs text-slate-600">{evidence.description || "Ver foto"}</span></a>)}</div></div> : null}</Panel>) : <Panel><p className="text-center text-slate-500">Todavía no hay entregas registradas.</p></Panel>}</section></> : null}
    <p className="text-center text-xs text-slate-400">Este enlace es privado. Si lo compartes, otra persona podrá consultar este historial.</p>
  </div></main>;
}

function Panel({ children }: { children: React.ReactNode }) { return <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">{children}</section>; }
function ImpactCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="rounded-xl bg-slate-50 p-4"><span className="text-emerald-700">{icon}</span><p className="mt-2 text-xs text-slate-500">{label}</p><p className="mt-1 text-xl font-bold">{value}</p></div>; }
