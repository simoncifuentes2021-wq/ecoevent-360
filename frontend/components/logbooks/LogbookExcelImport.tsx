"use client";

import { useEffect, useState } from "react";
import { FileSpreadsheet } from "lucide-react";
import { ModalShell } from "@/components/common/ModalShell";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/common/ToastProvider";
import { getEventStaff } from "@/lib/api/staff";
import { getLogbookTemplate, getLogbookTemplates, importLogbookXlsx, previewLogbookXlsx } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";
import type { EventStaff } from "@/types/staff";
import type { LogbookImportPreview } from "@/types/logbook";

export function LogbookExcelImport({eventId,onDone}:{eventId:string;onDone:()=>Promise<void>}) {
  const {toast}=useToast();
  const [open,setOpen]=useState(false); const [file,setFile]=useState<File|null>(null); const [preview,setPreview]=useState<LogbookImportPreview|null>(null);
  const [phase,setPhase]=useState<"idle"|"parsing"|"preview"|"importing"|"success">("idle"); const [error,setError]=useState("");
  const [staff,setStaff]=useState<EventStaff[]>([]); const [versions,setVersions]=useState<Array<{id:string;name:string}>>([]); const [versionId,setVersionId]=useState("");
  const [participants,setParticipants]=useState<string[]>([]); const [supervisor,setSupervisor]=useState(""); const [opens,setOpens]=useState("08:00"); const [due,setDue]=useState("20:00"); const [visible,setVisible]=useState(false);
  useEffect(()=>{if(!open)return;Promise.all([getEventStaff(eventId),getLogbookTemplates()]).then(async([members,list])=>{setStaff(members);const details=await Promise.all(list.items.filter(t=>t.status==="ACTIVE").map(t=>getLogbookTemplate(t.id)));const published=details.flatMap(t=>t.versions.filter(v=>v.status==="PUBLISHED").map(v=>({id:v.id,name:`${t.name} · v${v.version_number}`})));setVersions(published);setVersionId(published[0]?.id||"");}).catch(cause=>setError(logbookError(cause)));},[eventId,open]);
  async function analyze(){if(!file)return;setPhase("parsing");setError("");try{const result=await previewLogbookXlsx(eventId,file);setPreview(result);setPhase("preview");}catch(cause){setError(logbookError(cause,"No se pudo analizar el Excel."));setPhase("idle");}}
  async function confirm(){if(!file||!preview||preview.errors.length||!versionId||!participants.length)return;setPhase("importing");setError("");try{const result=await importLogbookXlsx(eventId,file,{file_sha256:preview.file_sha256,template_version_id:versionId,participant_ids:participants,supervisor_id:supervisor||null,opens_at_local:opens,due_at_local:due,timezone:"America/Santiago",client_visibility:visible,base_name:"Bitácora diaria"});setPhase("success");toast({title:`${result.instances_created} bitácoras creadas correctamente`,tone:"success"});await onDone();}catch(cause){setError(logbookError(cause,"No se pudo importar la planificación."));setPhase("preview");}}
  return <><Button onClick={()=>setOpen(true)} variant="secondary"><FileSpreadsheet className="mr-1 h-4 w-4"/>Importar planificación Excel</Button>{open?<ModalShell title="Importar planificación Excel" description="Analiza primero el archivo; ninguna bitácora se crea hasta confirmar." onClose={()=>{if(phase!=="importing")setOpen(false)}}><div className="max-h-[75vh] space-y-4 overflow-y-auto">
    <input accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={phase==="parsing"||phase==="importing"} onChange={e=>{setFile(e.target.files?.[0]||null);setPreview(null);setPhase("idle")}} type="file"/>
    {!preview?<Button disabled={!file||phase==="parsing"} onClick={()=>void analyze()}>{phase==="parsing"?"Analizando…":"Analizar"}</Button>:<><div className="grid grid-cols-2 gap-2 rounded-xl bg-slate-50 p-3 text-sm"><p>Actividades<br/><strong>{preview.activities_count}</strong></p><p>Fechas<br/><strong>{preview.dates_count}</strong></p><p>X encontradas<br/><strong>{preview.scheduled_items_count}</strong></p><p>Bitácoras<br/><strong>{preview.instances_to_create}</strong></p></div>
    {[...preview.errors,...preview.warnings].map((issue,index)=><p className={preview.errors.includes(issue)?"rounded bg-red-50 p-2 text-sm text-red-700":"rounded bg-amber-50 p-2 text-sm text-amber-800"} key={`${issue.code}-${index}`}>{issue.message}{issue.row?` · fila ${issue.row}`:""}{issue.column?` · columna ${issue.column}`:""}{issue.value?` · “${issue.value}”`:""}</p>)}
    {!preview.errors.length?<><label className="grid gap-1 text-sm">Plantilla base<select className="rounded-xl border p-2" value={versionId} onChange={e=>setVersionId(e.target.value)}>{versions.map(v=><option key={v.id} value={v.id}>{v.name}</option>)}</select></label>
    <fieldset className="rounded-xl border p-3"><legend className="text-sm font-medium">Participantes</legend>{staff.filter(m=>!["CLIENT","ADMIN","SUPER_ADMIN"].includes(m.user?.role||"")).map(m=><label className="mt-2 flex gap-2 text-sm" key={m.user_id}><input checked={participants.includes(m.user_id)} onChange={e=>setParticipants(c=>e.target.checked?[...c,m.user_id]:c.filter(id=>id!==m.user_id))} type="checkbox"/>{m.user?.full_name||m.user_id}</label>)}</fieldset>
    <label className="grid gap-1 text-sm">Supervisor<select className="rounded-xl border p-2" value={supervisor} onChange={e=>setSupervisor(e.target.value)}><option value="">Sin supervisor</option>{staff.filter(m=>m.user?.role==="SUPERVISOR").map(m=><option key={m.user_id} value={m.user_id}>{m.user?.full_name}</option>)}</select></label>
    <div className="grid grid-cols-2 gap-2"><label className="text-sm">Apertura<input className="block w-full rounded-xl border p-2" type="time" value={opens} onChange={e=>setOpens(e.target.value)}/></label><label className="text-sm">Vencimiento<input className="block w-full rounded-xl border p-2" type="time" value={due} onChange={e=>setDue(e.target.value)}/></label></div><label className="flex gap-2 text-sm"><input checked={visible} onChange={e=>setVisible(e.target.checked)} type="checkbox"/>Visible para cliente</label>
    <Button disabled={!participants.length||!versionId||phase==="importing"||phase==="success"} onClick={()=>void confirm()}>{phase==="importing"?"Importando…":phase==="success"?"Importación completada":"Confirmar importación"}</Button></>:null}</>}
    {error?<p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>:null}<Button onClick={()=>setOpen(false)} variant="secondary">Cerrar</Button>
  </div></ModalShell>:null}</>;
}
