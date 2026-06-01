"use client";

import { CalendarClock, MapPin, User } from "lucide-react";
import type { ReactNode } from "react";

import { ModalShell } from "@/components/common/ModalShell";
import { PriorityBadge } from "@/components/tasks/PriorityBadge";
import { TaskStatusBadge } from "@/components/tasks/TaskStatusBadge";
import type { Task } from "@/types/task";

function dateTime(value?: string | null) {
  return value ? new Intl.DateTimeFormat("es-CL", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)) : "Sin fecha";
}

export function TaskDetailPanel({ task, onClose }: { task: Task; onClose: () => void }) {
  return (
    <ModalShell title={task.title} description={task.description || "Detalle operativo de tarea."} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2"><TaskStatusBadge status={task.status} /><PriorityBadge priority={task.priority} /></div>
        <Info icon={<MapPin className="h-4 w-4" />} label="Zona" value={task.zone?.name || "Sin zona"} />
        <Info icon={<User className="h-4 w-4" />} label="Responsable" value={task.assignee?.full_name || task.assigned_user?.full_name || "Sin asignar"} />
        <Info icon={<CalendarClock className="h-4 w-4" />} label="Programacion" value={dateTime(task.scheduled_at)} />
        {task.observation ? <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">{task.observation}</div> : null}
      </div>
    </ModalShell>
  );
}

function Info({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border p-3 text-sm"><span className="text-emerald-700">{icon}</span><span className="font-semibold">{label}:</span><span className="text-slate-600">{value}</span></div>;
}
