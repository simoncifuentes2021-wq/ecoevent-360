"use client";

/* eslint-disable react-hooks/exhaustive-deps -- Reload only when the event identity changes. */

import { useEffect, useMemo, useRef, useState } from "react";

import { ModalShell } from "@/components/common/ModalShell";
import { LogbookDialog } from "@/components/logbooks/LogbookDialog";
import { Button } from "@/components/ui/button";
import {
  createLogbookRecurrence, finishLogbookRecurrence, getLogbookRecurrences,
  getLogbookRecurrenceOccurrences, getLogbookTemplate, getLogbookTemplates,
  pauseLogbookRecurrence, previewLogbookRecurrence,
  rescheduleLogbookRecurrenceOccurrence, resumeLogbookRecurrence,
  skipLogbookRecurrenceOccurrence, updateLogbookRecurrence,
} from "@/lib/api/logbooks";
import { getEventStaff } from "@/lib/api/staff";
import { logbookError } from "@/lib/logbook-errors";
import type { LogbookInstance, LogbookRecurrenceFrequency, LogbookRecurrencePayload, LogbookRecurrenceSeries, LogbookTemplateDetail } from "@/types/logbook";
import type { EventStaff } from "@/types/staff";

const dayLabels = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];
const frequencyLabels: Record<LogbookRecurrenceFrequency,string> = {DAILY:"Diario",WEEKLY:"Semanal",MONTHLY:"Mensual"};
const statusLabels: Record<string,string> = {ACTIVE:"Activa",PAUSED:"Pausada",FINISHED:"Finalizada",CANCELLED:"Cancelada"};

export function LogbookRecurrencePanel({ eventId, onChanged }: { eventId:string; onChanged:()=>Promise<void> }) {
  const [series,setSeries]=useState<LogbookRecurrenceSeries[]>([]);
  const [creating,setCreating]=useState(false);
  const [error,setError]=useState("");
  const [busyId,setBusyId]=useState("");
  const [editing,setEditing]=useState<LogbookRecurrenceSeries|null>(null);
  async function load(){try{setSeries(await getLogbookRecurrences(eventId));setError("");}catch(cause){setError(logbookError(cause,"No se pudieron cargar las recurrencias."));}}
  useEffect(()=>{void load();},[eventId]);
  async function transition(item:LogbookRecurrenceSeries, action:"pause"|"resume"|"finish"){
    if(busyId)return;setBusyId(item.id);setError("");
    try{if(action==="pause")await pauseLogbookRecurrence(item.id);else if(action==="resume")await resumeLogbookRecurrence(item.id);else await finishLogbookRecurrence(item.id);await load();await onChanged();}
    catch(cause){setError(logbookError(cause,"No se pudo cambiar la serie."));}finally{setBusyId("");}
  }
  return <section aria-labelledby="recurrence-title" className="space-y-3 rounded-2xl border bg-slate-50 p-4">
    <div className="flex flex-wrap items-center justify-between gap-2"><div><h3 className="font-semibold" id="recurrence-title">Bitácoras recurrentes</h3><p className="text-sm text-slate-600">Cada fecha crea una ejecución independiente.</p></div><Button onClick={()=>setCreating(true)}>Crear recurrencia</Button></div>
    {error?<p className="text-sm text-red-700" role="alert">{error}</p>:null}
    {series.length===0?<p className="text-sm text-slate-500">No hay series configuradas.</p>:<div className="grid gap-2">{series.map(item=><article className="rounded-xl border bg-white p-3" key={item.id}>
      <div className="flex flex-wrap justify-between gap-2"><div><p className="font-medium">{item.name}</p><p className="text-xs text-slate-500">{frequencyLabels[item.frequency]} · cada {item.interval} · {statusLabels[item.status]} · {item.timezone}</p><p className="text-xs text-slate-500">Generadas: {item.generated_count} · Próxima: {item.next_occurrence_date?new Date(`${item.next_occurrence_date}T12:00:00`).toLocaleDateString("es-CL"):"sin pendientes"}</p></div><div className="flex flex-wrap gap-2">{["ACTIVE","PAUSED"].includes(item.status)?<Button disabled={busyId===item.id} onClick={()=>setEditing(item)} size="sm" variant="secondary">Editar participantes futuros</Button>:null}{item.status==="ACTIVE"?<Button disabled={busyId===item.id} onClick={()=>void transition(item,"pause")} size="sm" variant="secondary">Pausar</Button>:item.status==="PAUSED"?<Button disabled={busyId===item.id} onClick={()=>void transition(item,"resume")} size="sm">Reanudar</Button>:null}{["ACTIVE","PAUSED"].includes(item.status)?<Button disabled={busyId===item.id} onClick={()=>void transition(item,"finish")} size="sm" variant="secondary">Finalizar</Button>:null}</div></div>
      <OccurrenceManager item={item} changed={async()=>{await load();await onChanged();}}/>
    </article>)}</div>}
    {creating?<RecurrenceForm eventId={eventId} close={()=>setCreating(false)} done={async()=>{setCreating(false);await load();await onChanged();}}/>:null}
    {editing?<FutureParticipantsDialog eventId={eventId} item={editing} close={()=>setEditing(null)} done={async()=>{setEditing(null);await load();await onChanged();}}/>:null}
  </section>;
}

function FutureParticipantsDialog({eventId,item,close,done}:{eventId:string;item:LogbookRecurrenceSeries;close:()=>void;done:()=>Promise<void>}){
  const [staff,setStaff]=useState<EventStaff[]>([]);const [participants,setParticipants]=useState<string[]>(item.participant_ids);const [loading,setLoading]=useState(true);const [saving,setSaving]=useState(false);const [error,setError]=useState("");
  useEffect(()=>{getEventStaff(eventId).then(setStaff).catch(cause=>setError(logbookError(cause))).finally(()=>setLoading(false));},[eventId]);
  async function save(){if(!participants.length||saving)return;setSaving(true);setError("");try{await updateLogbookRecurrence(item.id,{participant_ids:participants,revision:item.revision});await done();}catch(cause){setError(logbookError(cause,"No se pudieron actualizar los participantes futuros."));}finally{setSaving(false);}}
  return <LogbookDialog busy={saving} confirmDisabled={loading||participants.length===0} confirmLabel="Aplicar hacia el futuro" description="Solo se actualizan ocurrencias futuras sin actividad. Las respuestas, evidencias y participantes históricos se conservan." error={error} onClose={close} onConfirm={()=>void save()} open title="Editar participantes futuros"><fieldset className="max-h-72 overflow-y-auto rounded-xl border p-3"><legend className="text-sm font-medium">Participantes del evento</legend>{loading?<p className="text-sm text-slate-500">Cargando participantes...</p>:staff.filter(member=>!["CLIENT","ADMIN","SUPER_ADMIN"].includes(member.user?.role||"")).map(member=><label className="mt-2 flex gap-2 text-sm" key={member.user_id}><input type="checkbox" checked={participants.includes(member.user_id)} onChange={event=>setParticipants(current=>event.target.checked?[...current,member.user_id]:current.filter(id=>id!==member.user_id))}/>{member.user?.full_name||member.user_id}</label>)}</fieldset></LogbookDialog>;
}

function OccurrenceManager({item,changed}:{item:LogbookRecurrenceSeries;changed:()=>Promise<void>}){
  const [open,setOpen]=useState(false);const [occurrences,setOccurrences]=useState<LogbookInstance[]>([]);const [loading,setLoading]=useState(false);const [target,setTarget]=useState<LogbookInstance|null>(null);const [action,setAction]=useState<"skip"|"reschedule"|null>(null);const [replacement,setReplacement]=useState("");const [reason,setReason]=useState("");const [error,setError]=useState("");
  async function load(){setLoading(true);try{setOccurrences(await getLogbookRecurrenceOccurrences(item.id));setOpen(true);setError("");}catch(cause){setError(logbookError(cause));}finally{setLoading(false);}}
  async function confirm(){if(!target||!target.occurrence_date||!action)return;setLoading(true);setError("");try{if(action==="skip")await skipLogbookRecurrenceOccurrence(item.id,target.occurrence_date,reason);else await rescheduleLogbookRecurrenceOccurrence(item.id,target.occurrence_date,replacement,reason);setAction(null);setTarget(null);setReason("");setReplacement("");await load();await changed();}catch(cause){setError(logbookError(cause,"No se pudo modificar la ocurrencia."));}finally{setLoading(false);}}
  return <div className="mt-3 border-t pt-3"><Button disabled={loading} onClick={()=>open?setOpen(false):void load()} size="sm" variant="ghost">{open?"Ocultar fechas":"Ver historial y próximas fechas"}</Button>{error&&!action?<p className="mt-2 text-sm text-red-700">{error}</p>:null}{open?<div className="mt-2 grid gap-2">{occurrences.map(occurrence=><div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-slate-50 p-2 text-sm" key={occurrence.id}><span>{occurrence.occurrence_date?new Date(`${occurrence.occurrence_date}T12:00:00`).toLocaleDateString("es-CL"):"Sin fecha"} · {occurrence.status}{occurrence.original_occurrence_date?" · reprogramada":""}</span>{occurrence.status==="SCHEDULED"?<span className="flex gap-1"><Button size="sm" variant="ghost" onClick={()=>{setTarget(occurrence);setAction("reschedule");setReplacement(occurrence.occurrence_date||"");}}>Reprogramar</Button><Button size="sm" variant="ghost" onClick={()=>{setTarget(occurrence);setAction("skip");}}>Omitir</Button></span>:null}</div>)}</div>:null}<LogbookDialog busy={loading} confirmDisabled={action==="skip"?!reason.trim():!replacement} confirmLabel={action==="skip"?"Omitir fecha":"Reprogramar"} description="Sólo se modifica esta ocurrencia; el historial y las demás fechas se conservan." error={error} onClose={()=>{setAction(null);setTarget(null);setError("");}} onConfirm={()=>void confirm()} open={Boolean(action)} title={action==="skip"?"Omitir ocurrencia":"Reprogramar ocurrencia"}>{action==="reschedule"?<label className="grid gap-1 text-sm">Nueva fecha<input className="rounded-xl border p-3" type="date" value={replacement} onChange={event=>setReplacement(event.target.value)}/></label>:null}<label className="mt-3 grid gap-1 text-sm">Motivo<textarea className="rounded-xl border p-3" maxLength={1000} value={reason} onChange={event=>setReason(event.target.value)}/></label></LogbookDialog></div>;
}

function RecurrenceForm({eventId,close,done}:{eventId:string;close:()=>void;done:()=>Promise<void>}){
  const [templates,setTemplates]=useState<LogbookTemplateDetail[]>([]);const [staff,setStaff]=useState<EventStaff[]>([]);
  const [versionId,setVersionId]=useState("");const [participants,setParticipants]=useState<string[]>([]);const [mode,setMode]=useState<"INDIVIDUAL"|"SHARED">("INDIVIDUAL");
  const [frequency,setFrequency]=useState<LogbookRecurrenceFrequency>("WEEKLY");const [interval,setInterval]=useState(1);const [weekdays,setWeekdays]=useState<number[]>([1]);
  const today=new Date().toISOString().slice(0,10);const [startDate,setStartDate]=useState(today);const [endMode,setEndMode]=useState<"END_DATE"|"COUNT">("END_DATE");const [endDate,setEndDate]=useState(today);const [count,setCount]=useState(12);
  const [opens,setOpens]=useState("09:00");const [due,setDue]=useState("18:00");const [preview,setPreview]=useState<string[]>([]);const [error,setError]=useState("");const [saving,setSaving]=useState(false);const [confirm,setConfirm]=useState(false);const flight=useRef(false);
  useEffect(()=>{Promise.all([getLogbookTemplates(),getEventStaff(eventId)]).then(async([list,members])=>{const details=await Promise.all(list.items.filter(item=>item.status==="ACTIVE").map(item=>getLogbookTemplate(item.id)));setTemplates(details);setStaff(members);setVersionId(details.flatMap(item=>item.versions).find(version=>version.status==="PUBLISHED")?.id||"");}).catch(cause=>setError(logbookError(cause)));},[eventId]);
  const versions=useMemo(()=>templates.flatMap(template=>template.versions.filter(version=>version.status==="PUBLISHED").map(version=>({...version,name:template.name}))),[templates]);
  const rule={frequency,interval,weekdays:frequency==="WEEKLY"?weekdays:undefined,day_of_month:frequency==="MONTHLY"?Number(startDate.slice(8,10)):undefined,start_date:startDate,end_mode:endMode,end_date:endMode==="END_DATE"?endDate:undefined,max_occurrences:endMode==="COUNT"?count:undefined,opens_at_local:opens,due_at_local:due,timezone:"America/Santiago"} as const;
  const valid=Boolean(versionId&&participants.length&&startDate&&opens<due&&(endMode==="COUNT"?count>0:endDate>=startDate)&&(frequency!=="WEEKLY"||weekdays.length));
  async function showPreview(){setError("");try{const result=await previewLogbookRecurrence({...rule,limit:12});setPreview(result.dates);}catch(cause){setError(logbookError(cause,"No se pudo calcular la vista previa."));}}
  async function save(){if(!valid||flight.current)return;flight.current=true;setSaving(true);setError("");try{const payload:LogbookRecurrencePayload={...rule,template_version_id:versionId,assignment_mode:mode,participant_ids:participants,client_visibility:false};await createLogbookRecurrence(eventId,payload);await done();}catch(cause){setError(logbookError(cause,"No se pudo crear la recurrencia."));}finally{flight.current=false;setSaving(false);}}
  return <ModalShell title="Programar bitácora recurrente" description="Las fechas generadas mantienen respuestas y evidencias separadas." onClose={()=>{if(!saving)close();}}><div className="max-h-[75vh] space-y-4 overflow-y-auto pr-1">
    <label className="grid gap-1 text-sm">Plantilla publicada<select className="rounded-xl border p-3" disabled={saving} value={versionId} onChange={event=>setVersionId(event.target.value)}>{versions.map(version=><option key={version.id} value={version.id}>{version.name} · v{version.version_number}</option>)}</select></label>
    <label className="grid gap-1 text-sm">Modalidad<select className="rounded-xl border p-3" value={mode} onChange={event=>setMode(event.target.value as typeof mode)}><option value="INDIVIDUAL">Individual</option><option value="SHARED">Compartida</option></select></label>
    <fieldset className="rounded-xl border p-3"><legend className="text-sm font-medium">Participantes</legend>{staff.filter(member=>!["CLIENT","ADMIN","SUPER_ADMIN"].includes(member.user?.role||"")).map(member=><label className="mt-2 flex gap-2 text-sm" key={member.user_id}><input type="checkbox" checked={participants.includes(member.user_id)} onChange={event=>setParticipants(current=>event.target.checked?[...current,member.user_id]:current.filter(id=>id!==member.user_id))}/>{member.user?.full_name||member.user_id}</label>)}</fieldset>
    <div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm">Repetir<select className="rounded-xl border p-3" value={frequency} onChange={event=>setFrequency(event.target.value as LogbookRecurrenceFrequency)}><option value="DAILY">Diario</option><option value="WEEKLY">Semanal</option><option value="MONTHLY">Mensual</option></select></label><label className="grid gap-1 text-sm">Cada<input className="rounded-xl border p-3" min={1} max={52} type="number" value={interval} onChange={event=>setInterval(Number(event.target.value))}/></label></div>
    {frequency==="WEEKLY"?<fieldset className="rounded-xl border p-3"><legend className="text-sm font-medium">Días de la semana</legend><div className="flex flex-wrap gap-3">{dayLabels.map((label,index)=><label className="flex gap-1 text-sm" key={label}><input type="checkbox" checked={weekdays.includes(index)} onChange={event=>setWeekdays(current=>event.target.checked?[...current,index].sort():current.filter(day=>day!==index))}/>{label}</label>)}</div></fieldset>:null}
    {frequency==="MONTHLY"?<p className="rounded-lg bg-amber-50 p-3 text-sm">Se usa el día {Number(startDate.slice(8,10))}. Los meses que no tengan ese día se omiten.</p>:null}
    <label className="grid gap-1 text-sm">Fecha inicial<input className="rounded-xl border p-3" type="date" value={startDate} onChange={event=>setStartDate(event.target.value)}/></label>
    <div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm">Terminar por<select className="rounded-xl border p-3" value={endMode} onChange={event=>setEndMode(event.target.value as typeof endMode)}><option value="END_DATE">Fecha final</option><option value="COUNT">Cantidad</option></select></label>{endMode==="END_DATE"?<label className="grid gap-1 text-sm">Fecha final inclusiva<input className="rounded-xl border p-3" type="date" min={startDate} value={endDate} onChange={event=>setEndDate(event.target.value)}/></label>:<label className="grid gap-1 text-sm">Repeticiones<input className="rounded-xl border p-3" type="number" min={1} max={500} value={count} onChange={event=>setCount(Number(event.target.value))}/></label>}</div>
    <div className="grid gap-3 sm:grid-cols-2"><label className="grid gap-1 text-sm">Hora de apertura<input className="rounded-xl border p-3" type="time" value={opens} onChange={event=>setOpens(event.target.value)}/></label><label className="grid gap-1 text-sm">Hora de vencimiento<input className="rounded-xl border p-3" type="time" value={due} onChange={event=>setDue(event.target.value)}/></label></div><p className="text-sm text-slate-600">Zona horaria: America/Santiago</p>
    <Button disabled={!valid||saving} onClick={()=>void showPreview()} variant="secondary">Vista previa</Button>{preview.length?<ol className="grid grid-cols-2 gap-1 rounded-xl bg-slate-50 p-3 text-sm sm:grid-cols-3">{preview.map(day=><li key={day}>{new Date(`${day}T12:00:00`).toLocaleDateString("es-CL")}</li>)}</ol>:null}{error?<p className="text-sm text-red-700" role="alert">{error}</p>:null}<div className="flex justify-end gap-2"><Button variant="secondary" disabled={saving} onClick={close}>Cancelar</Button><Button disabled={!valid||saving} onClick={()=>setConfirm(true)}>Revisar y crear</Button></div>
  </div><LogbookDialog busy={saving} confirmLabel="Crear serie" description={`Se crearán ejecuciones ${frequencyLabels[frequency].toLowerCase()}s independientes. Las futuras permanecerán bloqueadas hasta su apertura.`} error={error} onClose={()=>setConfirm(false)} onConfirm={()=>void save()} open={confirm} title="Confirmar recurrencia"/></ModalShell>;
}
