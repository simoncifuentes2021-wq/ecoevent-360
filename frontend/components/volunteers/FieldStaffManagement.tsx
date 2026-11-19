"use client";

import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fieldStaffApi, type FieldStaff } from "@/lib/api/fieldStaff";
import type { RecyclingActivation } from "@/types/volunteer";

export function FieldStaffManagement({ eventId, activations }: { eventId: string; activations: RecyclingActivation[] }) {
  const [rows, setRows] = useState<FieldStaff[]>([]);
  const [name, setName] = useState("");
  const [rut, setRut] = useState("");
  const [activationIds, setActivationIds] = useState<string[]>([]);
  const [temporaryPassword, setTemporaryPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [origin, setOrigin] = useState("");
  const [linkCopied, setLinkCopied] = useState(false);
  const [portalEnabled, setPortalEnabled] = useState(false);
  const [portalStatusLoaded, setPortalStatusLoaded] = useState(false);
  const portalPath = `/public/personal-terreno/${eventId}`;
  const portalLink = `${origin}${portalPath}`;
  const load = useCallback(async () => { try { const [staffRows, portal] = await Promise.all([fieldStaffApi.list(eventId), fieldStaffApi.portalStatus(eventId)]); setRows(staffRows); setPortalEnabled(portal.enabled); setPortalStatusLoaded(true); setError(""); } catch (reason) { setPortalStatusLoaded(false); setError(reason instanceof Error ? reason.message : "No se pudo cargar el personal."); } }, [eventId]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { setOrigin(window.location.origin); setLinkCopied(false); setPortalStatusLoaded(false); }, [eventId]);
  async function copyPortalLink() {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${portalPath}`);
      setLinkCopied(true);
    } catch {
      setError("No se pudo copiar el enlace. Puedes seleccionarlo y copiarlo manualmente.");
    }
  }
  async function togglePortal() {
    if (!portalStatusLoaded) return;
    const nextEnabled = !portalEnabled;
    if (!nextEnabled && !window.confirm("Al cerrar el portal, el personal de este evento no podrá ingresar ni usar sesiones abiertas. El enlace y los registros se conservan; puedes reabrirlo cuando quieras.")) return;
    setBusy(true); setError("");
    try {
      const result = await fieldStaffApi.updatePortalStatus(eventId, nextEnabled);
      setPortalEnabled(result.enabled); setLinkCopied(false);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo cambiar el acceso al portal."); }
    finally { setBusy(false); }
  }
  async function create(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError("");
    try { const result = await fieldStaffApi.create(eventId, { full_name: name, rut, activation_ids: activationIds }); setRows((current) => [...current, result.staff].sort((a, b) => a.full_name.localeCompare(b.full_name))); setTemporaryPassword(result.temporary_password); setName(""); setRut(""); setActivationIds([]); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo crear el acceso."); } finally { setBusy(false); }
  }
  async function toggle(row: FieldStaff) { setBusy(true); try { const updated = await fieldStaffApi.update(row.id, { active: !row.active }); setRows((current) => current.map((item) => item.id === row.id ? updated : item)); } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo actualizar el acceso."); } finally { setBusy(false); } }
  async function reset(row: FieldStaff) { setBusy(true); try { setTemporaryPassword((await fieldStaffApi.reset(row.id)).temporary_password); } catch (reason) { setError(reason instanceof Error ? reason.message : "No se pudo renovar la contraseña."); } finally { setBusy(false); } }
  return <div className="space-y-5">
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h2 className="text-lg font-bold">Personal de terreno · {rows.length}</h2><p className="mt-1 text-sm text-slate-600">Crea accesos limitados a este evento y a los puntos asignados. No podrán entrar a la aplicación administrativa.</p>
      <div className={`mt-4 grid gap-3 rounded-xl border p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end ${portalEnabled ? "border-emerald-200 bg-emerald-50/60" : "border-rose-200 bg-rose-50/70"}`}><label className="grid min-w-0 gap-1 text-sm font-semibold text-slate-700">Enlace de acceso para el personal<input className="h-10 min-w-0 w-full rounded-lg border border-slate-200 bg-white px-3 font-normal text-slate-600" readOnly value={portalLink || portalPath} /></label><div className="flex flex-wrap gap-2"><Button type="button" variant="secondary" disabled={!portalStatusLoaded || !portalEnabled} onClick={() => void copyPortalLink()}>{linkCopied ? "Enlace copiado" : "Copiar enlace"}</Button>{portalStatusLoaded && portalEnabled ? <a className="inline-flex h-10 items-center rounded-xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-800 hover:bg-slate-50" href={portalPath} target="_blank" rel="noreferrer">Abrir</a> : <span className="inline-flex h-10 items-center rounded-lg px-2 text-sm font-semibold text-rose-800">{portalStatusLoaded ? "Enlace bloqueado" : "Verificando acceso…"}</span>}</div></div>
      <div className={`mt-3 flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${!portalStatusLoaded ? "border-slate-200 bg-slate-50" : portalEnabled ? "border-slate-200 bg-slate-50" : "border-rose-200 bg-rose-50"}`}><div><strong className={!portalStatusLoaded ? "text-slate-700" : portalEnabled ? "text-emerald-800" : "text-rose-800"}>{!portalStatusLoaded ? "Verificando portal" : portalEnabled ? "Portal abierto" : "Portal cerrado"}</strong><p className="mt-0.5 text-sm text-slate-600">{!portalStatusLoaded ? "Consultando el estado de acceso de este evento." : portalEnabled ? "El personal asignado puede iniciar sesión en este evento." : "Nadie puede iniciar sesión; también se bloquean las sesiones que estaban abiertas."}</p></div><Button type="button" disabled={busy || !portalStatusLoaded} variant={portalEnabled ? "destructive" : "primary"} onClick={() => void togglePortal()}>{busy ? "Guardando…" : !portalStatusLoaded ? "Cargando…" : portalEnabled ? "Revocar acceso al portal" : "Reactivar portal"}</Button></div>
      <form className="mt-4 grid gap-3 rounded-xl bg-slate-50 p-4 md:grid-cols-2" onSubmit={(event) => void create(event)}><label className="grid gap-1 text-sm font-medium">Nombre completo<Input required maxLength={180} value={name} onChange={(event) => setName(event.target.value)} /></label><label className="grid gap-1 text-sm font-medium">RUT válido<Input required value={rut} onChange={(event) => setRut(event.target.value)} placeholder="12.345.678-5" /></label><fieldset className="md:col-span-2"><legend className="mb-2 text-sm font-semibold">Puntos donde podrá operar</legend><div className="grid gap-2 sm:grid-cols-2">{activations.map((activation) => <label className="flex items-center gap-2 rounded-lg border bg-white p-2 text-sm" key={activation.id}><input checked={activationIds.includes(activation.id)} className="accent-emerald-700" onChange={(event) => setActivationIds((current) => event.target.checked ? [...current, activation.id] : current.filter((id) => id !== activation.id))} type="checkbox" />{activation.name}<span className="text-xs text-slate-500">{activation.status === "ACTIVE" ? "· Recibiendo" : ""}</span></label>)}</div></fieldset><Button className="md:col-span-2 md:justify-self-end" disabled={busy || activationIds.length === 0}>{busy ? "Guardando…" : "Crear acceso y contraseña temporal"}</Button></form>
      {temporaryPassword ? <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm"><strong>Entrega esta contraseña al encargado ahora; solo se muestra en esta sesión.</strong><p className="mt-2 break-all font-mono">{temporaryPassword}</p><p className="mt-2">Al ingresar, deberá cambiarla antes de operar.</p><Button className="mt-2" size="sm" variant="secondary" onClick={() => setTemporaryPassword("")}>Ocultar contraseña</Button></div> : null}
    </section>
    {error ? <p className="rounded-xl bg-rose-50 p-3 text-sm text-rose-800">{error}</p> : null}
    <section className="space-y-2">{rows.map((row) => <article className="rounded-xl border border-slate-200 bg-white p-4" key={row.id}><div className="flex flex-wrap items-center justify-between gap-3"><div><strong>{row.full_name}</strong><p className="text-sm text-slate-500">{row.rut} · {row.activation_names.join(", ")}</p><span className={`text-xs font-semibold ${row.active ? "text-emerald-700" : "text-slate-500"}`}>{row.active ? "Acceso activo" : "Acceso desactivado"}{row.must_change_password ? " · Debe cambiar contraseña" : ""}</span></div><div className="flex gap-2"><Button disabled={busy} size="sm" variant="secondary" onClick={() => void reset(row)}>Nueva contraseña</Button><Button disabled={busy} size="sm" variant={row.active ? "ghost" : "secondary"} onClick={() => void toggle(row)}>{row.active ? "Desactivar" : "Activar"}</Button></div></div><details className="mt-3 border-t pt-2"><summary className="cursor-pointer text-sm font-semibold text-emerald-800">Cambiar puntos asignados</summary><div className="mt-3 grid gap-2 sm:grid-cols-2">{activations.map((activation) => <label className="flex items-center gap-2 rounded-lg bg-slate-50 p-2 text-sm" key={activation.id}><input className="accent-emerald-700" type="checkbox" defaultChecked={row.activation_ids.includes(activation.id)} data-activation-id={activation.id} data-staff-id={row.id} />{activation.name}</label>)}</div><Button className="mt-3" size="sm" variant="secondary" disabled={busy} onClick={(event) => { const ids = Array.from(document.querySelectorAll<HTMLInputElement>(`input[data-staff-id="${row.id}"]:checked`)).map((input) => input.dataset.activationId!).filter(Boolean); setBusy(true); void fieldStaffApi.update(row.id, { activation_ids: ids }).then((updated) => setRows((current) => current.map((item) => item.id === row.id ? updated : item))).catch((reason) => setError(reason instanceof Error ? reason.message : "No se pudieron guardar los puntos.")).finally(() => setBusy(false)); }}>Guardar puntos</Button></details></article>)}{rows.length === 0 ? <p className="rounded-xl border border-dashed p-6 text-center text-sm text-slate-500">Todavía no hay personal de terreno para este evento.</p> : null}</section>
  </div>;
}
