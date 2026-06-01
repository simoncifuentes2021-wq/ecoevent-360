"use client";

import Link from "next/link";
import { CalendarClock, Camera, CheckCircle, MapPin, PlayCircle, ShieldAlert } from "lucide-react";

import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import { Button } from "@/components/ui/button";
import type { Task } from "@/types/task";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)) : "Sin horario";
}

export function WorkerTaskCard({ task, onStart, onComplete }: { task: Task; onStart: (task: Task) => void; onComplete: (task: Task) => void }) {
  const description = task.description?.trim();
  const snippet = description ? (description.length > 120 ? `${description.slice(0, 120)}...` : description) : "";
  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-lg font-bold text-slate-950">{task.title}</p>
          <p className="mt-1 text-sm text-slate-600">{task.event?.name || "Evento asignado"}</p>
        </div>
        <PriorityBadge priority={task.priority} />
      </div>
      <div className="mt-4 flex flex-wrap gap-2"><TaskStatusBadge status={task.status} /></div>
      <div className="mt-4 grid gap-2 text-sm text-slate-600">
        <span className="flex items-center gap-2"><MapPin className="h-4 w-4 text-emerald-700" />{task.zone?.name || "Sin zona"}</span>
        <span className="flex items-center gap-2"><CalendarClock className="h-4 w-4 text-emerald-700" />{dateTime(task.scheduled_at)}</span>
      </div>
      {description ? <p className="mt-4 text-sm text-slate-700">{snippet}</p> : null}
      <div className="mt-5 grid gap-2">
        {task.status === "PENDING" ? <Button className="h-12" onClick={() => onStart(task)}><PlayCircle className="h-5 w-5" />Iniciar</Button> : null}
        {task.status === "PENDING" || task.status === "IN_PROGRESS" ? <Button className="h-12" variant="secondary" onClick={() => onComplete(task)}><CheckCircle className="h-5 w-5" />Completar</Button> : null}
        <Link href={`/worker/tareas/${task.id}`}><Button className="h-12 w-full" variant="ghost">Ver detalle</Button></Link>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <Link href={`/worker/subir-evidencia?task_id=${task.id}&event_id=${task.event_id}`}><Button className="w-full" variant="secondary"><Camera className="h-4 w-4" />Evidencia</Button></Link>
        <Link href={`/worker/reportar-incidencia?event_id=${task.event_id}`}><Button className="w-full" variant="secondary"><ShieldAlert className="h-4 w-4" />Incidencia</Button></Link>
      </div>
    </div>
  );
}
