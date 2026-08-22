"use client";

import { useMemo, useState } from "react";
import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { EnvironmentalAction, EnvironmentalActionInput, EnvironmentalActionType, EnvironmentalMethodology } from "@/types/environmental";
import type { EventSession } from "@/types/eventSession";

const TYPES: Array<[EnvironmentalActionType, string]> = [["ELECTRIC_LIGHTING_TOWER", "Torre fotovoltaica"], ["ELECTRIC_MOTORCYCLE", "Moto eléctrica"], ["ELECTRIC_CART", "Carrito eléctrico"], ["SOLAR_ENERGY", "Energía solar"], ["ELECTRIC_VEHICLE", "Vehículo eléctrico"], ["BIKE_MOBILITY", "Movilidad en bicicleta"], ["PUBLIC_TRANSPORT", "Transporte público"], ["OTHER", "Otra solución"]];
const fieldClass = "h-10 w-full rounded-md border bg-white px-3 text-sm outline-none focus:border-emerald-600 focus:ring-2 focus:ring-emerald-100";
const normalizedDecimal = (value?: string | null, fallback = "") => value == null ? fallback : value.replace(/(\.\d*?[1-9])0+$|\.0+$/, "$1");
const formatNumber = (value: number) => new Intl.NumberFormat("es-CL", { maximumFractionDigits: 6 }).format(value);

export function EnvironmentalActionForm({ action, sessions, methodologies, saving, onClose, onSave }: { action?: EnvironmentalAction | null; sessions: EventSession[]; methodologies: EnvironmentalMethodology[]; saving: boolean; onClose: () => void; onSave: (value: EnvironmentalActionInput) => Promise<void> }) {
  const [type, setType] = useState<EnvironmentalActionType>(action?.action_type ?? "ELECTRIC_LIGHTING_TOWER");
  const [scope, setScope] = useState<"EVENT" | "SHOW">(action?.session_id ? "SHOW" : "EVENT");
  const [sessionId, setSessionId] = useState(action?.session_id ?? "");
  const [methodologyId, setMethodologyId] = useState(action?.methodology_id ?? "");
  const [name, setName] = useState(action?.name ?? "");
  const [quantity, setQuantity] = useState(normalizedDecimal(action?.quantity_used, "1"));
  const [hours, setHours] = useState(normalizedDecimal(action?.hours_used));
  const [distance, setDistance] = useState(normalizedDecimal(action?.distance_km));
  const [energy, setEnergy] = useState(normalizedDecimal(action?.energy_input_mode === "PER_UNIT_HOUR" ? action.energy_per_unit_hour_kwh : action?.energy_kwh));
  const [notes, setNotes] = useState(action?.notes ?? "");
  const [error, setError] = useState("");
  const options = useMemo(() => methodologies.filter((item) => item.action_type === type && item.is_active), [methodologies, type]);
  const needsHours = type === "ELECTRIC_LIGHTING_TOWER" || type === "ELECTRIC_CART";
  const needsDistance = ["ELECTRIC_MOTORCYCLE", "ELECTRIC_CART", "ELECTRIC_VEHICLE", "BIKE_MOBILITY", "PUBLIC_TRANSPORT"].includes(type);
  const perUnitHour = type === "ELECTRIC_LIGHTING_TOWER" && (!action || action.energy_input_mode === "PER_UNIT_HOUR");
  const totalEnergy = Number(energy) * Number(quantity) * Number(hours);
  const hasPreview = perUnitHour && Number(energy) > 0 && Number(quantity) > 0 && Number(hours) > 0;

  async function submit(event: React.FormEvent) {
    event.preventDefault(); setError("");
    if (scope === "SHOW" && !sessionId) return setError("Selecciona un show.");
    if (!name.trim()) return setError("Ingresa el nombre de la acción.");
    if (Number(quantity) <= 0) return setError("Ingresa la cantidad de torres.");
    if (perUnitHour && Number(hours) <= 0) return setError("Ingresa horas de funcionamiento mayores que cero.");
    if (perUnitHour && Number(energy) <= 0) return setError("Ingresa la energía de una torre por hora.");
    if (type === "SOLAR_ENERGY" && energy === "") return setError("Ingresa los kWh generados.");
    const payload: EnvironmentalActionInput = { action_type: type, name: name.trim(), quantity_used: Number(quantity), session_id: scope === "SHOW" ? sessionId : null, methodology_id: methodologyId || null, notes: notes || undefined };
    if (hours !== "") payload.hours_used = Number(hours);
    if (distance !== "") payload.distance_km = Number(distance);
    if (perUnitHour) { payload.energy_per_unit_hour_kwh = Number(energy); payload.energy_input_mode = "PER_UNIT_HOUR"; }
    else if (energy !== "") { payload.energy_kwh = Number(energy); payload.energy_input_mode = "TOTAL_MEASURED"; payload.energy_source = "MEASURED"; }
    await onSave(payload);
  }

  return <ModalShell title={action ? "Editar equipo o acción" : "Registrar equipo o acción"} description="El backend validará el alcance y realizará el cálculo trazable." onClose={onClose} size="lg"><form className="space-y-5" onSubmit={submit}>
    <fieldset><legend className="mb-2 text-sm font-bold">1. Alcance</legend><div className="grid gap-2 sm:grid-cols-2">{(["EVENT", "SHOW"] as const).map((item) => <button className={`rounded-xl border p-3 text-left text-sm ${scope === item ? "border-emerald-600 bg-emerald-50 font-semibold" : "border-slate-200"}`} key={item} onClick={() => setScope(item)} type="button">{item === "EVENT" ? "Evento completo" : "Show específico"}</button>)}</div>{scope === "SHOW" ? <select aria-label="Show" className={`${fieldClass} mt-3`} value={sessionId} onChange={(e) => setSessionId(e.target.value)}><option value="">Selecciona un show</option>{sessions.filter((s) => !s.archived_at).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select> : null}</fieldset>
    <fieldset><legend className="mb-2 text-sm font-bold">2. Tipo de solución</legend><select aria-label="Tipo de solución" className={fieldClass} value={type} onChange={(e) => { setType(e.target.value as EnvironmentalActionType); setMethodologyId(""); setEnergy(""); }}>{TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></fieldset>
    <fieldset className="grid gap-3 sm:grid-cols-2"><legend className="mb-2 text-sm font-bold sm:col-span-2">3. Datos operacionales</legend><label className="text-sm">Nombre<Input required maxLength={180} value={name} onChange={(e) => setName(e.target.value)} /></label><label className="text-sm">Cantidad<Input min="0.0001" required step="any" type="number" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label>{needsHours ? <label className="text-sm">Horas de funcionamiento<Input min="0.0001" required={perUnitHour} step="any" type="number" value={hours} onChange={(e) => setHours(e.target.value)} /></label> : null}{needsDistance ? <label className="text-sm">Distancia total (km)<Input min="0" step="any" type="number" value={distance} onChange={(e) => setDistance(e.target.value)} /></label> : null}<label className="text-sm sm:col-span-2">{perUnitHour ? "Energía de 1 torre por hora (kWh)" : type === "SOLAR_ENERGY" ? "Energía generada (kWh)" : "Energía total (kWh)"}<Input min={perUnitHour ? "0.000001" : "0"} placeholder={perUnitHour ? "0,75" : undefined} required={perUnitHour} step="any" type="number" value={energy} onChange={(e) => setEnergy(e.target.value)} />{perUnitHour ? <span className="mt-1 block text-xs text-slate-500">Ingresa la energía correspondiente a una sola torre durante una hora. EcoEvent calculará automáticamente la energía total según la cantidad de torres y las horas de funcionamiento.</span> : null}</label></fieldset>
    {perUnitHour ? <section aria-live="polite" className="rounded-xl border border-emerald-200 bg-emerald-50 p-4"><h3 className="font-bold">Cálculo de energía</h3><p className="mt-2 text-sm">{formatNumber(Number(energy) || 0)} kWh × {formatNumber(Number(quantity) || 0)} torres × {formatNumber(Number(hours) || 0)} h = {hasPreview ? formatNumber(totalEnergy) : "0"} kWh</p><p className="mt-2 text-lg font-bold text-emerald-800">Energía total calculada: {hasPreview ? formatNumber(totalEnergy) : "0"} kWh</p>{hasPreview ? <p className="mt-1 text-xs text-emerald-800">Equivale a {formatNumber(totalEnergy)} kWh para {formatNumber(Number(quantity))} torres durante {formatNumber(Number(hours))} h.</p> : null}</section> : null}
    <fieldset><legend className="mb-2 text-sm font-bold">4. Metodología</legend><select aria-label="Metodología" className={fieldClass} value={methodologyId} onChange={(e) => setMethodologyId(e.target.value)}><option value="">Sin metodología (guardar como pendiente)</option>{options.map((m) => <option key={m.id} value={m.id}>{m.name}: {m.baseline_technology} vs {m.actual_technology}</option>)}</select>{options.length === 0 ? <p className="mt-2 text-sm text-amber-700">No hay una metodología documentada para este tipo. No se inventarán resultados.</p> : null}</fieldset>
    <label className="block text-sm">Observaciones<textarea className={`${fieldClass} min-h-20 py-2`} maxLength={4000} value={notes} onChange={(e) => setNotes(e.target.value)} /></label>{error ? <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}<div className="flex justify-end gap-2"><Button disabled={saving} type="button" variant="secondary" onClick={onClose}>Cancelar</Button><Button disabled={saving} type="submit">{saving ? "Guardando..." : action ? "Guardar cambios" : "Guardar acción"}</Button></div>
  </form></ModalShell>;
}
