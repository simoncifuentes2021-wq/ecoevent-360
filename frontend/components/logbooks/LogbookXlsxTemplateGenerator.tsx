"use client";

import { Download } from "lucide-react";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { getEvent } from "@/lib/api/events";
import { downloadLogbookXlsxTemplate } from "@/lib/api/logbooks";
import { logbookError } from "@/lib/logbook-errors";

export function LogbookXlsxTemplateGenerator({eventId}:{eventId:string}) {
  const [minimum,setMinimum]=useState(""); const [maximum,setMaximum]=useState("");
  const [start,setStart]=useState(""); const [end,setEnd]=useState("");
  const [loading,setLoading]=useState(true); const [downloading,setDownloading]=useState(false); const [error,setError]=useState("");
  useEffect(()=>{let active=true;setLoading(true);void getEvent(eventId).then(event=>{if(!active)return;const first=event.start_date.slice(0,10);const last=event.end_date.slice(0,10);setMinimum(first);setMaximum(last);setStart(first);setEnd(last);}).catch(cause=>{if(active)setError(logbookError(cause,"No se pudo cargar el período del evento."));}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[eventId]);
  const days=start&&end?Math.floor((new Date(`${end}T12:00:00`).getTime()-new Date(`${start}T12:00:00`).getTime())/86400000)+1:0;
  const valid=Boolean(start&&end&&start<=end&&start>=minimum&&end<=maximum&&days<=366);
  async function download(){if(!valid||downloading)return;setDownloading(true);setError("");try{const result=await downloadLogbookXlsxTemplate(eventId,start,end);const url=URL.createObjectURL(result.blob);const anchor=document.createElement("a");anchor.href=url;anchor.download=result.filename;document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);}catch(cause){setError(logbookError(cause,"No se pudo generar la plantilla."));}finally{setDownloading(false);}}
  return <section className="space-y-3 rounded-xl border border-emerald-200 bg-emerald-50 p-3"><div><h3 className="font-semibold text-emerald-900">Generar plantilla oficial</h3><p className="text-xs text-emerald-800">Selecciona un rango dentro del evento. El Excel incluirá esas fechas y el formato exacto aceptado por la aplicación.</p></div><div className="grid grid-cols-2 gap-2"><label className="text-sm">Desde<input className="block w-full rounded-xl border bg-white p-2" disabled={loading||downloading} max={maximum} min={minimum} onChange={event=>setStart(event.target.value)} type="date" value={start}/></label><label className="text-sm">Hasta<input className="block w-full rounded-xl border bg-white p-2" disabled={loading||downloading} max={maximum} min={minimum} onChange={event=>setEnd(event.target.value)} type="date" value={end}/></label></div>{start&&end?<p className={valid?"text-xs text-emerald-800":"text-xs font-medium text-red-700"}>{valid?`${days} fechas serán incluidas.`:"El rango debe estar dentro del evento, en orden correcto y no superar 366 días."}</p>:null}<Button disabled={!valid||loading||downloading} onClick={()=>void download()} type="button" variant="secondary"><Download className="mr-1 h-4 w-4"/>{downloading?"Generando…":"Descargar plantilla Excel"}</Button>{error?<p className="rounded bg-red-50 p-2 text-sm text-red-700">{error}</p>:null}</section>;
}
