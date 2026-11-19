"use client";

import { useMemo, useState } from "react";

import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { isoToChileLocalInput } from "@/lib/chile-time";
import type { ContributionInput, ActivationInput, VolunteerInput } from "@/lib/api/volunteers";
import type { MaterialContribution, RecyclableMaterial, VolunteerResolve } from "@/types/volunteer";

const field = "grid gap-1.5 text-sm font-medium text-slate-700";
const area = "min-h-24 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100";

export function ActivationFormModal({ eventId, materials, onClose, onSave, saving, initial }: {
  eventId: string;
  materials: RecyclableMaterial[];
  onClose: () => void;
  onSave: (value: ActivationInput) => Promise<void>;
  saving: boolean;
  initial?: Partial<ActivationInput>;
}) {
  const [name, setName] = useState(initial?.name || "");
  const [description, setDescription] = useState(initial?.description || "");
  const [locationName, setLocationName] = useState(initial?.location_name || "");
  const [address, setAddress] = useState(initial?.address || "");
  const [startsAt, setStartsAt] = useState(initial?.starts_at ? isoToChileLocalInput(initial.starts_at) : "");
  const [endsAt, setEndsAt] = useState(initial?.ends_at ? isoToChileLocalInput(initial.ends_at) : "");
  const [capacity, setCapacity] = useState(initial?.capacity ? String(initial.capacity) : "");
  const [allowedMaterialIds, setAllowedMaterialIds] = useState<string[]>(initial?.allowed_material_ids || []);
  const editing = Boolean(initial?.name);
  return <ModalShell title={editing ? "Editar activación" : "Crear activación"} description="Cada activación registra su lugar, fecha, participantes y aportes dentro del evento seleccionado." onClose={onClose} size="lg">
    <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => { event.preventDefault(); void onSave({ event_id: eventId, name: name.trim(), description: description.trim() || null, location_name: locationName.trim() || null, address: address.trim() || null, starts_at: startsAt, ends_at: endsAt || null, capacity: capacity ? Number(capacity) : null, allowed_material_ids: allowedMaterialIds }); }}>
      <label className={`${field} sm:col-span-2`}>Nombre de la activación<Input required maxLength={180} value={name} onChange={(e) => setName(e.target.value)} placeholder="Recicla Temuco — Plaza Aníbal Pinto" /></label>
      <label className={field}>Lugar<Input maxLength={180} value={locationName} onChange={(e) => setLocationName(e.target.value)} placeholder="Plaza Aníbal Pinto" /></label>
      <label className={field}>Dirección<Input maxLength={1000} value={address} onChange={(e) => setAddress(e.target.value)} /></label>
      <label className={field}>Inicio<input className="h-11 rounded-xl border border-slate-200 px-3" required type="datetime-local" value={startsAt} onChange={(e) => setStartsAt(e.target.value)} /></label>
      <label className={field}>Término (opcional)<input className="h-11 rounded-xl border border-slate-200 px-3" type="datetime-local" value={endsAt} onChange={(e) => setEndsAt(e.target.value)} /></label>
      <label className={field}>Capacidad de inscripción (opcional)<Input min="1" type="number" value={capacity} onChange={(e) => setCapacity(e.target.value)} /></label>
      <label className={`${field} sm:col-span-2`}>Descripción<textarea className={area} maxLength={3000} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
      <fieldset className="sm:col-span-2 rounded-xl border border-slate-200 p-4"><legend className="px-1 text-sm font-semibold text-slate-800">Materiales que recibirá este punto</legend><p className="mb-3 text-xs text-slate-500">Se eligen del catálogo compartido de Residuos. Solo estos aparecerán al registrar aportes.</p><div className="grid gap-2 sm:grid-cols-2">{materials.map((material) => <label className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm" key={material.id}><input checked={allowedMaterialIds.includes(material.id)} className="h-4 w-4 accent-emerald-700" onChange={(e) => setAllowedMaterialIds((current) => e.target.checked ? [...current, material.id] : current.filter((id) => id !== material.id))} type="checkbox" />{material.name}</label>)}</div>{!materials.length ? <p className="text-sm text-amber-700">No hay materiales reciclables activos en el catálogo de Residuos.</p> : null}</fieldset>
      <ModalActions onClose={onClose} saving={saving} disabled={allowedMaterialIds.length === 0} label={editing ? "Guardar cambios" : "Crear activación"} />
    </form>
  </ModalShell>;
}

export function VolunteerFormModal({ onClose, onSave, saving, consentText, initialEmail }: {
  onClose: () => void;
  onSave: (value: VolunteerInput) => Promise<void>;
  saving: boolean;
  consentText: string;
  initialEmail?: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState(initialEmail || "");
  const [phone, setPhone] = useState("");
  const [organization, setOrganization] = useState("");
  const [consent, setConsent] = useState(false);
  return <ModalShell title="Registrar voluntario" description="La persona se identifica por su correo y podrá participar en distintas activaciones sin duplicarse." onClose={onClose}>
    <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void onSave({ full_name: name.trim(), email: email.trim(), phone: phone.trim(), organization: organization.trim() || null, consent_accepted: true }); }}>
      <label className={field}>Nombre completo<Input required autoComplete="name" maxLength={180} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label className={field}>Correo electrónico<Input required autoComplete="email" type="email" maxLength={254} value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      <label className={field}>Teléfono<Input required autoComplete="tel" type="tel" maxLength={40} value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
      <label className={field}>Organización (opcional)<Input maxLength={180} value={organization} onChange={(e) => setOrganization(e.target.value)} /></label>
      <label className="flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-3 text-sm leading-5 text-slate-700"><input className="mt-1 h-4 w-4 accent-emerald-700" checked={consent} onChange={(e) => setConsent(e.target.checked)} required type="checkbox" /><span>{consentText}</span></label>
      <ModalActions onClose={onClose} saving={saving} disabled={!consent} label="Guardar voluntario" />
    </form>
  </ModalShell>;
}

export function ContributionForm({ activationId, materials, volunteer, initial, onCancel, onSave, saving }: {
  activationId: string;
  materials: RecyclableMaterial[];
  volunteer: VolunteerResolve;
  initial?: MaterialContribution;
  onCancel: () => void;
  onSave: (value: ContributionInput, image: File | null) => Promise<void>;
  saving: boolean;
}) {
  const firstMaterial = materials[0]?.id || "";
  const [items, setItems] = useState<Array<{ material_id: string; weight_kg: string }>>(() => initial?.items.length
    ? initial.items.map((item) => ({ material_id: item.material_id, weight_kg: String(item.weight_kg) }))
    : [{ material_id: firstMaterial, weight_kg: "" }]);
  const [notes, setNotes] = useState(initial?.notes || "");
  const [image, setImage] = useState<File | null>(null);
  const [fileLabel, setFileLabel] = useState("");
  const total = useMemo(() => items.reduce((sum, item) => sum + (Number(item.weight_kg.replace(",", ".")) || 0), 0), [items]);
  const available = materials;

  return <ModalShell title={initial ? "Corregir entrega" : "Registrar aporte"} description={`${volunteer.full_name} · ${volunteer.unique_code} · acumulado del evento ${new Intl.NumberFormat("es-CL", { maximumFractionDigits: 3 }).format(Number(volunteer.total_weight_kg_in_event))} kg`} onClose={onCancel} size="lg">
    <form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void onSave({ volunteer_id: volunteer.id, items: items.map((item) => ({ material_id: item.material_id, weight_kg: item.weight_kg.replace(",", ".") })), notes: notes.trim() || null, ...(initial ? {} : { idempotency_key: crypto.randomUUID() }) }, image); }}>
      <div className="rounded-2xl bg-slate-50 p-4">
        <div className="grid grid-cols-[minmax(0,1fr)_6rem_2rem] gap-2 px-1 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 sm:grid-cols-[minmax(0,1fr)_8rem_2.5rem]"><span>Material</span><span>Peso kg</span><span /></div>
        <div className="space-y-2">
          {items.map((item, index) => <div className="grid grid-cols-[minmax(0,1fr)_6rem_2rem] gap-2 sm:grid-cols-[minmax(0,1fr)_8rem_2.5rem]" key={index}>
            <select aria-label={`Material ${index + 1}`} className="h-11 min-w-0 rounded-xl border border-slate-200 bg-white px-3 text-sm focus:border-emerald-600 focus:outline-none" required value={item.material_id} onChange={(e) => setItems((current) => current.map((row, i) => i === index ? { ...row, material_id: e.target.value } : row))}>
              <option value="">Seleccionar</option>{available.map((material) => <option disabled={items.some((row, i) => i !== index && row.material_id === material.id)} key={material.id} value={material.id}>{material.name}</option>)}
            </select>
            <Input aria-label={`Peso en kg para la línea ${index + 1}`} inputMode="decimal" min="0.001" max="1000000" required step="0.001" type="number" value={item.weight_kg} onChange={(e) => setItems((current) => current.map((row, i) => i === index ? { ...row, weight_kg: e.target.value } : row))} />
            <Button aria-label={`Quitar línea ${index + 1}`} className="h-11 w-10 px-0" disabled={items.length <= 1} variant="secondary" onClick={() => setItems((current) => current.filter((_, i) => i !== index))} type="button">×</Button>
          </div>)}
        </div>
        <Button className="mt-3" disabled={items.length >= available.length || available.length === 0} size="sm" variant="secondary" onClick={() => setItems((current) => [...current, { material_id: available.find((material) => !current.some((row) => row.material_id === material.id))?.id || "", weight_kg: "" }])} type="button">+ Agregar material</Button>
        <div className="mt-4 flex items-center justify-between border-t border-slate-200 pt-3"><span className="font-semibold text-slate-700">Total de la entrega</span><strong className="text-xl text-emerald-800">{new Intl.NumberFormat("es-CL", { maximumFractionDigits: 3 }).format(total)} kg</strong></div>
      </div>
      {available.length === 0 ? <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">No hay materiales activos. Pide a administración que configure el catálogo.</p> : null}
      <label className={field}>Nota para el registro<textarea className={area} maxLength={2000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Observación opcional" /></label>
      {!initial ? <label className="grid gap-2 text-sm font-medium text-slate-700">Foto de la entrega (opcional)<input accept="image/*" capture="environment" className="block w-full rounded-xl border border-slate-200 p-2 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-emerald-50 file:px-3 file:py-2 file:font-semibold file:text-emerald-800" onChange={(e) => { const file = e.target.files?.[0] || null; setImage(file); setFileLabel(file?.name || ""); }} type="file" /><span className="text-xs font-normal text-slate-500">En teléfono podrás tomar una foto o elegir un archivo existente. Máximo según el límite de evidencias del sistema.</span>{fileLabel ? <span className="text-xs text-emerald-700">Lista: {fileLabel}</span> : null}</label> : null}
      <div className="flex flex-col-reverse justify-end gap-2 border-t pt-4 sm:flex-row"><Button className="w-full sm:w-auto" disabled={saving} onClick={onCancel} type="button" variant="secondary">Volver</Button><Button className="w-full sm:w-auto" disabled={saving || total <= 0 || !items.every((item) => item.material_id && Number(item.weight_kg) > 0)}>{saving ? "Guardando..." : initial ? "Guardar corrección" : "Registrar aporte"}</Button></div>
    </form>
  </ModalShell>;
}

function ModalActions({ onClose, saving, disabled, label }: { onClose: () => void; saving: boolean; disabled?: boolean; label: string }) {
  return <div className="flex flex-col-reverse justify-end gap-2 border-t pt-4 sm:col-span-2 sm:flex-row"><Button className="w-full sm:w-auto" disabled={saving} onClick={onClose} type="button" variant="secondary">Cancelar</Button><Button className="w-full sm:w-auto" disabled={saving || disabled}>{saving ? "Guardando..." : label}</Button></div>;
}
